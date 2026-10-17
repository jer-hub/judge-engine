"""Contest integrity: monitor (log-only) and strict (soft-block until teacher unlock)."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from django.db import transaction
from django.db.models import Count, F, Sum
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from submissions.models import Submission

from .models import Contest, ContestIntegrityEvent, ContestParticipant

ALLOWED_EVENT_TYPES = {c.value for c in ContestIntegrityEvent.EventType}
MAX_EVENTS_PER_REQUEST = 50
MAX_COUNT_PER_EVENT = 100
SAFE_META_KEYS = frozenset({"chars"})

FOCUS_SOFT_BLOCK_THRESHOLD = 5
PASTE_SOFT_BLOCK_THRESHOLD = 3

# Events that count toward focus soft-block in strict mode.
FOCUS_EVENT_TYPES = frozenset(
    {
        ContestIntegrityEvent.EventType.VISIBILITY_HIDDEN,
        ContestIntegrityEvent.EventType.WINDOW_BLUR,
        ContestIntegrityEvent.EventType.FULLSCREEN_EXIT,
    }
)
# Immediate soft-block (do not wait for threshold).
IMMEDIATE_BLOCK_TYPES = frozenset(
    {
        ContestIntegrityEvent.EventType.FULLSCREEN_EXIT,
        ContestIntegrityEvent.EventType.VISIBILITY_HIDDEN,
    }
)


def assert_can_post_events(contest: Contest, user) -> ContestParticipant:
    if not contest.integrity_monitoring:
        raise PermissionDenied("Integrity monitoring is disabled for this contest.")
    participant = ContestParticipant.objects.filter(contest=contest, user=user).first()
    if participant is None:
        raise PermissionDenied("You must register for the contest first.")
    now = timezone.now()
    if now < contest.start_time or now > contest.end_time_for(user):
        raise PermissionDenied(
            "Integrity events are only accepted during your contest window."
        )
    return participant


def _sanitize_meta(raw: Any) -> dict:
    if not isinstance(raw, dict):
        return {}
    out: dict[str, Any] = {}
    if "chars" in raw:
        try:
            chars = int(raw["chars"])
        except (TypeError, ValueError):
            chars = 0
        out["chars"] = max(0, min(chars, 1_000_000))
    return {k: v for k, v in out.items() if k in SAFE_META_KEYS}


def _apply_strict_counters(
    participant: ContestParticipant, event_type: str, count: int
) -> None:
    """Bump counters / set soft-block for a strict contest. Caller saves."""
    if event_type in FOCUS_EVENT_TYPES:
        participant.integrity_focus_since_ack += count
    if event_type == ContestIntegrityEvent.EventType.EDITOR_PASTE:
        participant.integrity_paste_since_ack += count
    if event_type in IMMEDIATE_BLOCK_TYPES:
        participant.integrity_blocked = True
    elif participant.integrity_focus_since_ack >= FOCUS_SOFT_BLOCK_THRESHOLD:
        participant.integrity_blocked = True
    elif participant.integrity_paste_since_ack >= PASTE_SOFT_BLOCK_THRESHOLD:
        participant.integrity_blocked = True


def record_events(contest: Contest, user, raw_events: list) -> dict[str, Any]:
    """Persist a batch of client events. Returns created count + block state."""
    participant = assert_can_post_events(contest, user)
    if not isinstance(raw_events, list):
        raise ValidationError({"events": "Must be a list."})
    if len(raw_events) > MAX_EVENTS_PER_REQUEST:
        raise ValidationError(
            {"events": f"At most {MAX_EVENTS_PER_REQUEST} events per request."}
        )

    to_create: list[ContestIntegrityEvent] = []
    for item in raw_events:
        if not isinstance(item, dict):
            raise ValidationError({"events": "Each event must be an object."})
        event_type = item.get("type") or item.get("event_type")
        if event_type not in ALLOWED_EVENT_TYPES:
            raise ValidationError({"events": f"Unknown event type: {event_type!r}."})
        if event_type == ContestIntegrityEvent.EventType.SOFT_BLOCK_ACK:
            raise ValidationError(
                {"events": "Teachers unlock soft-blocks via POST …/integrity-unlock/."}
            )
        count = item.get("count", 1)
        if isinstance(count, bool) or not isinstance(count, int) or count < 1:
            raise ValidationError({"events": "count must be a positive integer."})
        count = min(count, MAX_COUNT_PER_EVENT)
        to_create.append(
            ContestIntegrityEvent(
                contest=contest,
                user=user,
                event_type=event_type,
                count=count,
                meta=_sanitize_meta(item.get("meta")),
            )
        )

    with transaction.atomic():
        if to_create:
            ContestIntegrityEvent.objects.bulk_create(to_create)
        if contest.integrity_strict and contest.integrity_monitoring:
            participant = ContestParticipant.objects.select_for_update().get(
                pk=participant.pk
            )
            for ev in to_create:
                _apply_strict_counters(participant, ev.event_type, ev.count)
            participant.save(
                update_fields=[
                    "integrity_blocked",
                    "integrity_focus_since_ack",
                    "integrity_paste_since_ack",
                ]
            )

    return {
        "created": len(to_create),
        "integrity_blocked": participant.integrity_blocked,
        "integrity_focus_since_ack": participant.integrity_focus_since_ack,
        "integrity_paste_since_ack": participant.integrity_paste_since_ack,
    }


def unlock_soft_block(contest: Contest, teacher, username: str) -> dict[str, Any]:
    """Teacher clears a student's soft-block; students cannot self-unlock."""
    if not contest.integrity_monitoring or not contest.integrity_strict:
        raise ValidationError(
            {"detail": "Soft-block unlock is only used when strict monitoring is on."}
        )
    if not isinstance(username, str) or not username.strip():
        raise ValidationError({"username": "Required."})
    participant = (
        ContestParticipant.objects.filter(
            contest=contest, user__username__iexact=username.strip()
        )
        .select_related("user")
        .first()
    )
    if participant is None:
        raise ValidationError({"username": "Not registered for this contest."})
    with transaction.atomic():
        participant = ContestParticipant.objects.select_for_update().get(
            pk=participant.pk
        )
        if not participant.integrity_blocked:
            return {
                "username": participant.user.username,
                "integrity_blocked": False,
                "integrity_ack_count": participant.integrity_ack_count,
                "already_unblocked": True,
            }
        participant.integrity_blocked = False
        participant.integrity_focus_since_ack = 0
        participant.integrity_paste_since_ack = 0
        participant.integrity_ack_count = F("integrity_ack_count") + 1
        participant.save(
            update_fields=[
                "integrity_blocked",
                "integrity_focus_since_ack",
                "integrity_paste_since_ack",
                "integrity_ack_count",
            ]
        )
        ContestIntegrityEvent.objects.create(
            contest=contest,
            user=participant.user,
            event_type=ContestIntegrityEvent.EventType.SOFT_BLOCK_ACK,
            count=1,
            meta={"unlocked_by": teacher.username},
        )
        participant.refresh_from_db()
    return {
        "username": participant.user.username,
        "integrity_blocked": False,
        "integrity_ack_count": participant.integrity_ack_count,
        "already_unblocked": False,
    }


def assert_can_submit(contest: Contest | None, user) -> None:
    """Raise if strict soft-block is active for this contest submit."""
    if contest is None or not contest.integrity_monitoring or not contest.integrity_strict:
        return
    participant = ContestParticipant.objects.filter(contest=contest, user=user).first()
    if participant is not None and participant.integrity_blocked:
        raise ValidationError(
            {
                "contest": "Integrity soft-block: wait for a teacher to unlock your "
                "submissions for this contest."
            }
        )


def integrity_summary(contest: Contest) -> dict[str, Any]:
    """Admin summary: per-participant event totals, submit IPs, shared-IP flags."""
    participants = list(
        ContestParticipant.objects.filter(contest=contest)
        .select_related("user")
        .order_by("user__username")
    )
    user_ids = [p.user_id for p in participants]

    totals: dict[int, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for row in (
        ContestIntegrityEvent.objects.filter(contest=contest, user_id__in=user_ids)
        .values("user_id", "event_type")
        .annotate(total=Sum("count"))
    ):
        totals[row["user_id"]][row["event_type"]] = row["total"] or 0

    ip_by_user: dict[int, set[str]] = defaultdict(set)
    for row in Submission.objects.filter(
        contest=contest, user_id__in=user_ids
    ).values_list("user_id", "client_ip"):
        uid, ip = row
        if ip:
            ip_by_user[uid].add(str(ip))

    ip_to_users: dict[str, set[str]] = defaultdict(set)
    username_by_id = {p.user_id: p.user.username for p in participants}
    for uid, ips in ip_by_user.items():
        for ip in ips:
            ip_to_users[ip].add(username_by_id[uid])

    recent_limit = 20
    recent_by_user: dict[int, list[dict]] = defaultdict(list)
    if user_ids:
        # One query for all participants; slice the newest N per user in Python.
        for ev in ContestIntegrityEvent.objects.filter(
            contest=contest, user_id__in=user_ids
        ).order_by("user_id", "-created_at"):
            bucket = recent_by_user[ev.user_id]
            if len(bucket) >= recent_limit:
                continue
            bucket.append(
                {
                    "type": ev.event_type,
                    "count": ev.count,
                    "meta": ev.meta or {},
                    "created_at": ev.created_at.isoformat(),
                }
            )

    students = []
    for p in participants:
        uid = p.user_id
        ips = sorted(ip_by_user.get(uid, ()))
        shared: set[str] = set()
        for ip in ips:
            others = ip_to_users.get(ip, set()) - {p.user.username}
            shared.update(others)
        t = totals.get(uid, {})
        students.append(
            {
                "user_id": uid,
                "username": p.user.username,
                "visibility_hidden": t.get(
                    ContestIntegrityEvent.EventType.VISIBILITY_HIDDEN, 0
                ),
                "window_blur": t.get(ContestIntegrityEvent.EventType.WINDOW_BLUR, 0),
                "editor_paste": t.get(ContestIntegrityEvent.EventType.EDITOR_PASTE, 0),
                "fullscreen_exit": t.get(
                    ContestIntegrityEvent.EventType.FULLSCREEN_EXIT, 0
                ),
                "submit_ips": ips,
                "shared_ip_with": sorted(shared),
                "blocked": p.integrity_blocked,
                "ack_count": p.integrity_ack_count,
                "focus_since_ack": p.integrity_focus_since_ack,
                "paste_since_ack": p.integrity_paste_since_ack,
                "recent_events": recent_by_user.get(uid, []),
            }
        )

    return {
        "contest_id": contest.id,
        "integrity_monitoring": contest.integrity_monitoring,
        "integrity_strict": contest.integrity_strict,
        "students": students,
        "event_counts": ContestIntegrityEvent.objects.filter(contest=contest).aggregate(
            n=Count("id")
        )["n"]
        or 0,
    }
