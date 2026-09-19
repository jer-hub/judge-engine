from celery.exceptions import TimeoutError as CeleryTimeout
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle
from rest_framework.views import APIView

from .run_serializers import RunPreviewSerializer


class RunRateThrottle(UserRateThrottle):
    scope = "runs"


class RunPreviewView(APIView):
    """Compile and run Java with custom stdin (no submission / scoreboard)."""

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

        async_result = preview_run.delay(
            source_code=data["source_code"],
            stdin=data.get("stdin", ""),
            time_limit_ms=problem.time_limit_ms,
            memory_limit_mb=problem.memory_limit_mb,
        )
        try:
            outcome = async_result.get(timeout=60)
        except CeleryTimeout:
            async_result.revoke(terminate=False)
            return Response(
                {
                    "status": "TimeLimitExceeded",
                    "compile_error": "",
                    "stdout": "",
                    "stderr": "Preview timed out waiting for the judge worker.",
                    "execution_time_ms": None,
                },
                status=status.HTTP_504_GATEWAY_TIMEOUT,
            )
        except Exception:
            return Response(
                {
                    "status": "RuntimeError",
                    "compile_error": "",
                    "stdout": "",
                    "stderr": "Preview failed. Please retry.",
                    "execution_time_ms": None,
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )

        return Response(
            {
                "status": outcome.get("status", "RuntimeError"),
                "compile_error": outcome.get("compile_error", ""),
                "stdout": outcome.get("stdout", ""),
                "stderr": outcome.get("stderr", ""),
                "execution_time_ms": outcome.get("execution_time_ms"),
            },
            status=status.HTTP_200_OK,
        )
