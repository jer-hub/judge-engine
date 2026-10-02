"""Admin view of the judging pipeline: workers, queues, submission states."""
from __future__ import annotations

import redis
from django.conf import settings
from django.db.models import Count, Min
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsAdmin
from submissions.models import Submission

# Celery's Redis broker keeps each queue as a list named after it.
QUEUES = ("judge", "preview", "celery")


def _worker_pings() -> list[dict]:
    from config.celery import app

    try:
        replies = app.control.inspect(timeout=1.0).ping() or {}
    except Exception:
        replies = {}
    return [
        {"name": name, "ok": reply.get("ok") == "pong"} for name, reply in sorted(replies.items())
    ]


def _queue_lengths() -> dict[str, int | None]:
    try:
        client = redis.from_url(settings.CELERY_BROKER_URL, socket_timeout=2, socket_connect_timeout=2)
        return {queue: client.llen(queue) for queue in QUEUES}
    except Exception:
        return {queue: None for queue in QUEUES}


class JudgeHealthView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        workers = _worker_pings()
        names = {w["name"].split("@")[0] for w in workers if w["ok"]}
        by_status = dict(
            Submission.objects.filter(
                status__in=[
                    Submission.Status.PENDING,
                    Submission.Status.JUDGING,
                    Submission.Status.SYSTEM_ERROR,
                ]
            )
            .values_list("status")
            .annotate(n=Count("id"))
        )
        oldest = Submission.objects.filter(status=Submission.Status.PENDING).aggregate(
            t=Min("submitted_at")
        )["t"]
        return Response(
            {
                "workers": workers,
                # The judge worker answers as judge@host, previews as preview@host.
                "judge_worker_up": "judge" in names,
                "preview_worker_up": "preview" in names,
                "queues": _queue_lengths(),
                "submissions": {
                    "pending": by_status.get(Submission.Status.PENDING, 0),
                    "judging": by_status.get(Submission.Status.JUDGING, 0),
                    "system_error": by_status.get(Submission.Status.SYSTEM_ERROR, 0),
                    "oldest_pending_seconds": (
                        int((timezone.now() - oldest).total_seconds()) if oldest else None
                    ),
                },
            }
        )
