import redis
from celery.result import AsyncResult
from django.conf import settings
from django.http import Http404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle
from rest_framework.views import APIView

from .run_serializers import RunPreviewSerializer

# How long a preview's owner record (and so its result) stays fetchable.
RUN_OWNER_TTL_SECONDS = 600
# A preview still queued after this is dropped (the student has long since
# stopped waiting); its result then reads as "Preview failed. Please retry."
RUN_QUEUE_EXPIRES_SECONDS = 300
PENDING_STATUSES = ("Pending", "Running")


class RunRateThrottle(UserRateThrottle):
    scope = "runs"


def _redis_client():
    return redis.from_url(settings.REDIS_URL, decode_responses=True)


def _owner_key(task_id: str) -> str:
    return f"run-owner:{task_id}"


class RunPreviewView(APIView):
    """Queue a compile-and-run with custom stdin (no submission / scoreboard).

    Returns 202 with a ``task_id`` immediately; poll ``RunPreviewResultView``.
    Web workers never block waiting for the judge.
    """

    permission_classes = [IsAuthenticated]
    throttle_classes = [RunRateThrottle]

    def post(self, request):
        serializer = RunPreviewSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        problem = data["problem"]

        from judge.tasks import preview_run

        async_result = preview_run.apply_async(
            kwargs={
                "source_code": data["source_code"],
                "stdin": data.get("stdin", ""),
                "time_limit_ms": problem.time_limit_ms,
                "memory_limit_mb": problem.memory_limit_mb,
            },
            expires=RUN_QUEUE_EXPIRES_SECONDS,
        )
        _redis_client().setex(
            _owner_key(async_result.id), RUN_OWNER_TTL_SECONDS, request.user.id
        )
        return Response(
            {"task_id": async_result.id, "status": "Pending"},
            status=status.HTTP_202_ACCEPTED,
        )


class RunPreviewResultView(APIView):
    """Poll a queued preview. Only the user who started it can read it."""

    permission_classes = [IsAuthenticated]

    def get(self, request, task_id: str):
        owner = _redis_client().get(_owner_key(task_id))
        if owner is None or owner != str(request.user.id):
            raise Http404

        result = AsyncResult(task_id)
        if result.state in ("PENDING", "RECEIVED"):
            return Response({"task_id": task_id, "status": "Pending"})
        if result.state in ("STARTED", "RETRY"):
            return Response({"task_id": task_id, "status": "Running"})
        if result.state != "SUCCESS":
            return Response(
                {
                    "task_id": task_id,
                    "status": "SystemError",
                    "compile_error": "",
                    "stdout": "",
                    "stderr": "Preview failed. Please retry.",
                    "execution_time_ms": None,
                }
            )

        outcome = result.result or {}
        return Response(
            {
                "task_id": task_id,
                "status": outcome.get("status", "RuntimeError"),
                "compile_error": outcome.get("compile_error", ""),
                "stdout": outcome.get("stdout", ""),
                "stderr": outcome.get("stderr", ""),
                "execution_time_ms": outcome.get("execution_time_ms"),
            }
        )
