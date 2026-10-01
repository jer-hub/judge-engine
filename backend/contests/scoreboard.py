"""ICPC-style scoreboard computation with optional Redis caching and freeze."""
from __future__ import annotations

import json
from collections import defaultdict
from typing import Any

import redis
from django.conf import settings
from django.utils import timezone

from submissions.models import Submission

from .models import Contest, ContestParticipant, ContestProblem

PENALTY_MINUTES_PER_WRONG = 20
CACHE_TTL_SECONDS = 5


def _redis_client():
    return redis.from_url(settings.REDIS_URL, decode_responses=True)


def build_scoreboard(contest: Contest, viewer=None) -> dict[str, Any]:
    cache_key = f"scoreboard:{contest.id}"
    is_admin = bool(viewer and getattr(viewer, "is_platform_admin", False))

    if not is_admin:
        try:
            client = _redis_client()
            cached = client.get(cache_key)
            if cached:
                payload = json.loads(cached)
                payload["cached"] = True
                return payload
        except Exception:
            pass

    # Students all get the same freeze-respecting board (it is cached under one
    # shared key), so no viewer's own post-freeze results are revealed here;
    # they still see their own verdicts on the submissions page.
    payload = _compute_scoreboard(contest, reveal_frozen=is_admin)
    if not is_admin and contest.status == "upcoming":
        # Don't reveal the problem set before the start.
        payload["problems"] = []
        for row in payload["standings"]:
            row["problems"] = []

    if not is_admin:
        try:
            client = _redis_client()
            client.setex(cache_key, CACHE_TTL_SECONDS, json.dumps(payload))
        except Exception:
            pass

    payload["cached"] = False
    return payload


def invalidate_scoreboard_cache(contest_id: int) -> None:
    try:
        client = _redis_client()
        client.delete(f"scoreboard:{contest_id}")
    except Exception:
        pass


def _compute_scoreboard(
    contest: Contest,
    reveal_frozen: bool = False,
) -> dict[str, Any]:
    problems = list(
        ContestProblem.objects.filter(contest=contest).select_related("problem")
    )
    participants = list(
        ContestParticipant.objects.filter(contest=contest).select_related("user")
    )
    problem_ids = [cp.problem_id for cp in problems]
    letter_by_problem = {cp.problem_id: cp.letter for cp in problems}

    submissions = (
        Submission.objects.filter(
            contest=contest,
            problem_id__in=problem_ids,
            submitted_at__gte=contest.start_time,
            submitted_at__lte=contest.end_time,
        )
        .select_related("user")
        .order_by("submitted_at", "id")
    )

    freeze_at = contest.freeze_at
    apply_freeze = bool(freeze_at and contest.status == "active" and not reveal_frozen)

    # user_id -> problem_id -> state
    state: dict[int, dict[int, dict[str, Any]]] = defaultdict(
        lambda: defaultdict(
            lambda: {
                "attempts": 0,
                "solved": False,
                "solve_time_min": None,
                "penalty": 0,
                "pending": False,
            }
        )
    )

    for sub in submissions:
        cell = state[sub.user_id][sub.problem_id]
        if cell["solved"]:
            continue

        hidden_by_freeze = (
            apply_freeze
            and freeze_at is not None
            and sub.submitted_at >= freeze_at
        )

        if hidden_by_freeze:
            cell["pending"] = True
            continue

        if sub.status in (
            Submission.Status.PENDING,
            Submission.Status.JUDGING,
        ):
            cell["pending"] = True
            continue

        if sub.status == Submission.Status.ACCEPTED:
            minutes = int(
                (sub.submitted_at - contest.start_time).total_seconds() // 60
            )
            cell["solved"] = True
            cell["solve_time_min"] = minutes
            cell["penalty"] = minutes + cell["attempts"] * PENALTY_MINUTES_PER_WRONG
            cell["attempts"] += 1
        elif sub.status in (
            Submission.Status.WRONG_ANSWER,
            Submission.Status.TIME_LIMIT_EXCEEDED,
            Submission.Status.MEMORY_LIMIT_EXCEEDED,
            Submission.Status.RUNTIME_ERROR,
        ):
            cell["attempts"] += 1
        # CompileError: ignored entirely, as in ICPC — no attempt, no penalty.

    rows = []
    for participant in participants:
        uid = participant.user_id
        solved = 0
        penalty = 0
        last_solve_min = 0
        cells = []
        for cp in problems:
            cell = state[uid][cp.problem_id]
            if cell["solved"]:
                solved += 1
                penalty += cell["penalty"]
                last_solve_min = max(last_solve_min, cell["solve_time_min"])
            cells.append(
                {
                    "letter": letter_by_problem[cp.problem_id],
                    "problem_id": cp.problem_id,
                    "solved": cell["solved"],
                    "attempts": cell["attempts"],
                    "solve_time_min": cell["solve_time_min"],
                    "pending": cell["pending"],
                }
            )
        rows.append(
            {
                "username": participant.user.username,
                "solved": solved,
                "penalty": penalty,
                "last_solve_min": last_solve_min,
                "problems": cells,
            }
        )

    # ICPC: more solved, then less penalty, then earlier last accepted solve.
    # Rows still equal on all three share a rank (username only orders them).
    def standing(r):
        return (-r["solved"], r["penalty"], r["last_solve_min"])

    rows.sort(key=lambda r: (*standing(r), r["username"]))
    for i, row in enumerate(rows):
        same_as_prev = i > 0 and standing(row) == standing(rows[i - 1])
        row["rank"] = rows[i - 1]["rank"] if same_as_prev else i + 1

    return {
        "contest_id": contest.id,
        "title": contest.title,
        "is_frozen": contest.is_frozen and not reveal_frozen,
        "freeze_at": freeze_at.isoformat() if freeze_at else None,
        "server_time": timezone.now().isoformat(),
        "problems": [
            {
                "letter": cp.letter,
                "problem_id": cp.problem_id,
                "slug": cp.problem.slug,
                "title": cp.problem.title,
            }
            for cp in problems
        ],
        "standings": rows,
    }
