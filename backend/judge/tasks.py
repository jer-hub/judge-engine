"""Celery tasks for judging submissions."""
from __future__ import annotations

import logging

from celery import shared_task
from django.db import transaction
from django.utils import timezone

logger = logging.getLogger("judge")


@shared_task(bind=True, max_retries=2, default_retry_delay=5)
def judge_submission(self, submission_id: int) -> dict:
    from contests.scoreboard import invalidate_scoreboard_cache
    from judge.executor import JudgeExecutor
    from submissions.models import Submission, SubmissionResult

    try:
        submission = Submission.objects.select_related("problem").get(pk=submission_id)
    except Submission.DoesNotExist:
        logger.error("Submission %s not found", submission_id)
        return {"error": "not_found"}

    if submission.status not in (
        Submission.Status.PENDING,
        Submission.Status.JUDGING,
    ):
        return {"status": submission.status, "skipped": True}

    submission.status = Submission.Status.JUDGING
    submission.save(update_fields=["status"])

    problem = submission.problem
    test_cases = [
        {
            "id": tc.id,
            "input_data": tc.input_data,
            "expected_output": tc.expected_output,
            "order": tc.order,
        }
        for tc in problem.test_cases.all().order_by("order", "id")
    ]

    if not test_cases:
        submission.status = Submission.Status.RUNTIME_ERROR
        submission.compile_error = "No test cases configured for this problem."
        submission.judged_at = timezone.now()
        submission.save(update_fields=["status", "compile_error", "judged_at"])
        return {"status": submission.status}

    try:
        executor = JudgeExecutor()
        outcome = executor.judge_submission_source(
            source_code=submission.source_code,
            test_cases=test_cases,
            time_limit_ms=problem.time_limit_ms,
            memory_limit_mb=problem.memory_limit_mb,
            run_all_tests=problem.run_all_tests,
        )
    except Exception as exc:
        logger.exception("Judge failed for submission %s: %s", submission_id, exc)
        try:
            raise self.retry(exc=exc)
        except self.MaxRetriesExceededError:
            submission.status = Submission.Status.RUNTIME_ERROR
            submission.compile_error = "Internal judge error. Please retry or contact an admin."
            submission.judged_at = timezone.now()
            submission.save(update_fields=["status", "compile_error", "judged_at"])
            return {"status": submission.status, "error": "internal"}

    with transaction.atomic():
        SubmissionResult.objects.filter(submission=submission).delete()
        for item in outcome.get("results", []):
            SubmissionResult.objects.create(
                submission=submission,
                test_case_id=item["test_case_id"],
                verdict=item["verdict"],
                execution_time_ms=item.get("execution_time_ms"),
                stdout_snippet=item.get("stdout_snippet", ""),
                stderr_snippet=item.get("stderr_snippet", ""),
            )
        submission.status = outcome["status"]
        submission.compile_error = outcome.get("compile_error", "")
        submission.judged_at = timezone.now()
        submission.save(update_fields=["status", "compile_error", "judged_at"])

    if submission.contest_id:
        invalidate_scoreboard_cache(submission.contest_id)

    logger.info("Submission %s judged as %s", submission_id, submission.status)
    return {"status": submission.status, "results": len(outcome.get("results", []))}


@shared_task(bind=True, max_retries=1, default_retry_delay=3)
def preview_run(
    self,
    source_code: str,
    stdin: str,
    time_limit_ms: int,
    memory_limit_mb: int,
) -> dict:
    """Dry-run: compile + execute with custom stdin. No DB writes."""
    from judge.executor import JudgeExecutor

    try:
        executor = JudgeExecutor()
        result = executor.preview_run(
            source_code=source_code,
            stdin=stdin,
            time_limit_ms=time_limit_ms,
            memory_limit_mb=memory_limit_mb,
        )
        logger.info("Preview run status=%s time_ms=%s", result.get("status"), result.get("execution_time_ms"))
        return result
    except Exception as exc:
        logger.exception("Preview run failed: %s", exc)
        try:
            raise self.retry(exc=exc)
        except self.MaxRetriesExceededError:
            return {
                "status": "RuntimeError",
                "compile_error": "",
                "stdout": "",
                "stderr": "Internal sandbox error. Please retry.",
                "execution_time_ms": None,
            }
