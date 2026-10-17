from datetime import timedelta

from django.db import transaction
from django.db.models import (
    Count,
    DateTimeField,
    ExpressionWrapper,
    F,
    OuterRef,
    Q,
    Subquery,
    Value,
)
from django.db.models.functions import Coalesce
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.text import slugify
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle

from accounts.permissions import IsAdmin
from audit.mixins import AuditedViewSetMixin
from submissions.models import Submission

from .export import standings_csv
from . import clarifications as clar
from . import integrity as integ
from .models import Clarification, Contest, ContestParticipant
from .scoreboard import build_scoreboard, invalidate_scoreboard_cache
from .similarity import contest_similarity
from .serializers import (
    ContestDetailSerializer,
    ContestListSerializer,
    ContestWriteSerializer,
)

BULK_MAX_IDS = 50
BULK_ACTIONS = frozenset({"archive", "set_public", "set_invite_only"})


class IntegrityEventThrottle(UserRateThrottle):
    scope = "integrity-events"


class IntegrityUnlockThrottle(UserRateThrottle):
    scope = "integrity-unlock"


class ContestViewSet(AuditedViewSetMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Contest.objects.all().prefetch_related(
            "contest_problems__problem",
            "participants__user",
        )
        user = self.request.user
        is_admin = getattr(user, "is_platform_admin", False)
        if not is_admin:
            qs = qs.filter(is_archived=False).filter(
                Q(is_public=True) | Q(participants__user=user)
            ).distinct()

        if self.action == "list":
            qs = qs.annotate(
                problem_count=Count("contest_problems", distinct=True),
                blocked_count=Count(
                    "participants",
                    filter=Q(participants__integrity_blocked=True),
                    distinct=True,
                ),
                clarifications_waiting=Count(
                    "clarifications",
                    filter=Q(
                        clarifications__answered_at__isnull=True,
                        clarifications__question__gt="",
                    ),
                    distinct=True,
                ),
            )

        status_filter = self.request.query_params.get("status")
        now = timezone.now()
        if status_filter == "archived":
            if is_admin:
                qs = qs.filter(is_archived=True)
            else:
                qs = qs.none()
        else:
            # Non-archived lifecycle filters (admins browsing Active etc.).
            if is_admin and status_filter in ("upcoming", "active", "past", None, ""):
                if status_filter:
                    qs = qs.filter(is_archived=False)
            if status_filter in ("active", "past"):
                # The viewer's own end: a student with a time extension is still
                # in an "active" contest after the official end.
                extra = ContestParticipant.objects.filter(
                    contest=OuterRef("pk"), user_id=user.pk
                ).values("extra_minutes")[:1]
                qs = qs.annotate(
                    my_end=ExpressionWrapper(
                        F("end_time")
                        + Coalesce(Subquery(extra), 0) * Value(timedelta(minutes=1)),
                        output_field=DateTimeField(),
                    )
                )
            if status_filter == "upcoming":
                qs = qs.filter(start_time__gt=now, is_archived=False)
            elif status_filter == "active":
                qs = qs.filter(start_time__lte=now, my_end__gte=now, is_archived=False)
            elif status_filter == "past":
                qs = qs.filter(my_end__lt=now, is_archived=False)

        search = (self.request.query_params.get("search") or "").strip()
        if search:
            qs = qs.filter(title__icontains=search)
        # Re-assert Meta ordering after annotate/filter (pagination warning).
        return qs.order_by("-start_time")

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return ContestWriteSerializer
        if self.action == "retrieve":
            return ContestDetailSerializer
        return ContestListSerializer

    def get_permissions(self):
        if self.action in (
            "create", "update", "partial_update", "destroy",
            "reveal", "extensions", "standings_export", "answer_clarification",
            "similarity", "integrity", "integrity_unlock",
            "archive", "bulk",
        ):
            return [IsAuthenticated(), IsAdmin()]
        return [IsAuthenticated()]

    def destroy(self, request, *args, **kwargs):
        contest = self.get_object()
        now = timezone.now()
        has_subs = Submission.objects.filter(contest=contest).exists()
        upcoming_empty = now < contest.start_time and not has_subs
        if not contest.is_archived and not upcoming_empty:
            raise ValidationError(
                {
                    "detail": (
                        "Archive the contest first, or delete only an upcoming "
                        "contest with no submissions."
                    )
                }
            )
        return super().destroy(request, *args, **kwargs)

    def get_throttles(self):
        if self.action == "integrity_events":
            return [IntegrityEventThrottle()]
        if self.action == "integrity_unlock":
            return [IntegrityUnlockThrottle()]
        return super().get_throttles()

    @action(detail=False, methods=["post"], url_path="bulk")
    def bulk(self, request):
        """Admin: archive or visibility for many contests.
        Body: {"ids": [1,2], "action": "archive"|"set_public"|"set_invite_only"}."""
        ids = request.data.get("ids")
        action_name = request.data.get("action")
        if not isinstance(ids, list) or not ids:
            raise ValidationError({"ids": "Provide a non-empty list of contest ids."})
        if len(ids) > BULK_MAX_IDS:
            raise ValidationError({"ids": f"At most {BULK_MAX_IDS} contests."})
        if action_name not in BULK_ACTIONS:
            raise ValidationError(
                {"action": f"Must be one of: {', '.join(sorted(BULK_ACTIONS))}."}
            )
        clean_ids: list[int] = []
        for raw in ids:
            if isinstance(raw, bool) or not isinstance(raw, int):
                raise ValidationError({"ids": "Each id must be an integer."})
            clean_ids.append(raw)
        with transaction.atomic():
            qs = Contest.objects.filter(pk__in=clean_ids)
            if action_name == "archive":
                updated = qs.update(is_archived=True)
            elif action_name == "set_public":
                updated = qs.update(is_public=True)
            else:
                updated = qs.update(is_public=False)
        return Response({"updated": updated, "action": action_name})

    @action(detail=True, methods=["post"], url_path="archive")
    def archive(self, request, pk=None):
        """Admin: soft-archive or restore ({"archived": true|false})."""
        contest = self.get_object()
        archived = request.data.get("archived", True)
        if not isinstance(archived, bool):
            raise ValidationError({"archived": "Must be true or false."})
        contest.is_archived = archived
        contest.save(update_fields=["is_archived"])
        return Response(
            ContestListSerializer(contest, context={"request": request}).data
        )

    @action(detail=True, methods=["post"], url_path="register")
    def register(self, request, pk=None):
        contest = self.get_object()
        now = timezone.now()
        if now > contest.end_time:
            return Response(
                {"detail": "Contest has already ended."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        _, created = ContestParticipant.objects.get_or_create(
            contest=contest,
            user=request.user,
        )
        return Response(
            {"registered": True, "created": created},
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    @action(detail=True, methods=["get", "post"], url_path="clarifications")
    def clarifications(self, request, pk=None):
        """GET: what the viewer may see. POST: a student asks a question
        ({"question", "problem_letter"?}); an admin posts an announcement
        ({"answer"})."""
        contest = self.get_object()
        if request.method == "POST":
            if getattr(request.user, "is_platform_admin", False):
                item = clar.announce(contest, request.user, request.data)
            else:
                item = clar.ask_question(contest, request.user, request.data)
            return Response(
                clar.ClarificationSerializer(item, context={"request": request}).data,
                status=status.HTTP_201_CREATED,
            )
        items = clar.visible_clarifications(contest, request.user)
        return Response(
            clar.ClarificationSerializer(items, many=True, context={"request": request}).data
        )

    @action(
        detail=True,
        methods=["post"],
        url_path=r"clarifications/(?P<clarification_id>\d+)/answer",
    )
    def answer_clarification(self, request, pk=None, clarification_id=None):
        """Admin: answer a question ({"answer", "is_public"}); is_public shows
        it to every contestant."""
        contest = self.get_object()
        item = get_object_or_404(Clarification, pk=clarification_id, contest=contest)
        item = clar.answer(item, request.user, request.data)
        return Response(clar.ClarificationSerializer(item, context={"request": request}).data)

    @action(detail=True, methods=["get"], url_path="similarity")
    def similarity(self, request, pk=None):
        """Admin: pairs of students with suspiciously similar code per problem
        (?threshold=0.6, from 0.3 to 1). A lead to review, not proof."""
        contest = self.get_object()
        try:
            threshold = float(request.query_params.get("threshold", 0.6))
        except ValueError:
            raise ValidationError({"threshold": "Must be a number."}) from None
        if not 0.3 <= threshold <= 1:
            raise ValidationError({"threshold": "Must be between 0.3 and 1."})
        return Response({"threshold": threshold, "pairs": contest_similarity(contest, threshold)})

    @action(detail=True, methods=["post"], url_path="integrity-events")
    def integrity_events(self, request, pk=None):
        """Student: batch of warn-only proctoring signals during an active contest.
        Body: {"events": [{"type": "window_blur", "count": 1, "meta": {...}}]}."""
        contest = self.get_object()
        result = integ.record_events(
            contest, request.user, request.data.get("events", [])
        )
        return Response(result, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="integrity-unlock")
    def integrity_unlock(self, request, pk=None):
        """Admin: clear a student's soft-block ({"username"})."""
        contest = self.get_object()
        return Response(
            integ.unlock_soft_block(
                contest, request.user, request.data.get("username", "")
            )
        )

    @action(detail=True, methods=["get"], url_path="integrity")
    def integrity(self, request, pk=None):
        """Admin: per-participant focus/paste totals, submit IPs, shared-IP leads."""
        contest = self.get_object()
        return Response(integ.integrity_summary(contest))

    @action(detail=True, methods=["post"], url_path="reveal")
    def reveal(self, request, pk=None):
        """Admin: lift the scoreboard freeze now ({"revealed": true}), or
        freeze it again ({"revealed": false})."""
        contest = self.get_object()
        revealed = request.data.get("revealed", True)
        if not isinstance(revealed, bool):
            raise ValidationError({"revealed": "Must be true or false."})
        contest.results_revealed_at = timezone.now() if revealed else None
        contest.save(update_fields=["results_revealed_at"])
        invalidate_scoreboard_cache(contest.id)
        return Response(ContestDetailSerializer(contest, context={"request": request}).data)

    @action(detail=True, methods=["post"], url_path="extensions")
    def extensions(self, request, pk=None):
        """Admin: give a registered student extra minutes ({"username",
        "extra_minutes"}; 0 removes the extension)."""
        contest = self.get_object()
        username = request.data.get("username")
        extra = request.data.get("extra_minutes")
        if not isinstance(username, str) or not username.strip():
            raise ValidationError({"username": "Required."})
        if isinstance(extra, bool) or not isinstance(extra, int) or not 0 <= extra <= 24 * 60:
            raise ValidationError({"extra_minutes": "Whole minutes from 0 to 1440."})
        participant = (
            ContestParticipant.objects.filter(contest=contest, user__username__iexact=username.strip())
            .select_related("user")
            .first()
        )
        if participant is None:
            raise ValidationError({"username": "Not registered for this contest."})
        participant.extra_minutes = extra
        participant.save(update_fields=["extra_minutes"])
        invalidate_scoreboard_cache(contest.id)
        return Response(
            {
                "username": participant.user.username,
                "extra_minutes": participant.extra_minutes,
                "ends_at": contest.end_time_for(participant.user).isoformat(),
            }
        )

    @action(detail=True, methods=["get"], url_path="scoreboard")
    def scoreboard(self, request, pk=None):
        contest = self.get_object()
        data = build_scoreboard(contest, viewer=request.user)
        return Response(data)

    @action(detail=True, methods=["get"], url_path="standings-export")
    def standings_export(self, request, pk=None):
        """Admin: final standings as CSV; ?section= keeps one class section."""
        contest = self.get_object()
        section = request.query_params.get("section", "").strip() or None
        body = standings_csv(contest, viewer=request.user, section=section)
        name = slugify(contest.title) or f"contest-{contest.id}"
        if section:
            name += f"-{slugify(section) or 'section'}"
        response = HttpResponse(body, content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = f'attachment; filename="{name}-standings.csv"'
        return response
