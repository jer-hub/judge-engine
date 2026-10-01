"""Celery tasks for judging submissions."""
from __future__ import annotations

import logging
import uuid
from datetime import timedelta

from celery import shared_task
from celery.exceptions import SoftTimeLimitExceeded
from django.conf import settings
from django.db import transaction
from django.db.models import F, Q
from django.utils import timezone

logger = logging.getLogger("judge")

SYSTEM_ERROR_MESSAGE = (
    "Judging failed because of a server problem, not your code. "
    "It will be re-judged automatically."
)
# Automatic re-judges of a SystemError before it is left for an admin.
MAX_AUTO_REJUDGES = 3
SYSTEM_ERROR_RETRY_AFTER = timedelta(minutes=2)


def enqueue_judging(submission_id: int) -> bool:
    """Queue a submission for judging; False if the broker is unreachable.

    A failed enqueue leaves the submission Pending, and the recovery sweep
    queues it again once it goes stale, so callers need not fail the request.
    """
    from submissions.models import Submission

    Submission.objects.filter(pk=submission_id).update(enqueued_at=timezone.now())
    try:
        judge_submission.delay(submission_id)
    except Exception:
        logger.exception("Could not enqueue submission %s; the sweep will retry", submission_id)
        return False
    return True


def _record_outcome(
    submission_id: int,
    claim: uuid.UUID,
    status: str,
    compile_error: str = "",
    results: list[dict] | None = None,
) -> bool:
    """Write the verdict if this task still holds the claim.

    Returns False, writing nothing, when the claim was lost meanwhile (the
    submission was rejudged or recovered by the sweep).
    """
    from contests.scoreboard import invalidate_scoreboard_cache
    from submissions.models import Submission, SubmissionResult

    with transaction.atomic():
        submission = (
            Submission.objects.select_for_update()
            .filter(pk=submission_id, judge_claim=claim)
            .first()
        )
        if submission is None:
            logger.warning("Submission %s: claim lost, discarding stale verdict", submission_id)
            return False
        SubmissionResult.objects.filter(submission=submission).delete()
        SubmissionResult.objects.bulk_create(
            SubmissionResult(
                submission=submission,
                test_case_id=item["test_case_id"],
                verdict=item["verdict"],
                execution_time_ms=item.get("execution_time_ms"),
                stdout_snippet=item.get("stdout_snippet", ""),
                stderr_snippet=item.get("stderr_snippet", ""),
            )
            for item in results or []
        )
        submission.status = status
        submission.compile_error = compile_error
        submission.judged_at = timezone.now()
        submission.judge_claim = None
        submission.judging_started_at = None
        submission.save(
            update_fields=[
                "status", "compile_error", "judged_at", "judge_claim", "judging_started_at",
            ]
        )
    if submission.contest_id:
        invalidate_scoreboard_cache(submission.contest_id)
    return True


@shared_task(
    bind=True,
    max_retries=2,
    default_retry_delay=5,
    soft_time_limit=settings.JUDGE_TASK_SOFT_LIMIT_S,
    time_limit=settings.JUDGE_TASK_SOFT_LIMIT_S + 60,
)
def judge_submission(self, submission_id: int, claim: str | None = None) -> dict:
    from judge.executor import JudgeExecutor
    from submissions.models import Submission

    try:
        submission = Submission.objects.select_related("problem").get(pk=submission_id)
    except Submission.DoesNotExist:
        logger.error("Submission %s not found", submission_id)
        return {"error": "not_found"}

    # Claim atomically so a duplicate enqueue (double rejudge, the sweep)
    # cannot judge the same submission twice. A retry carries its claim.
    now = timezone.now()
    if claim is None:
        token = uuid.uuid4()
        claimed = Submission.objects.filter(
            pk=submission_id, status=Submission.Status.PENDING
        ).update(status=Submission.Status.JUDGING, judge_claim=token, judging_started_at=now)
    else:
        token = uuid.UUID(claim)
        claimed = Submission.objects.filter(
            pk=submission_id, status=Submission.Status.JUDGING, judge_claim=token
        ).update(judging_started_at=now)
    if not claimed:
        submission.refresh_from_db(fields=["status"])
        return {"status": submission.status, "skipped": True}

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
        # A setup mistake by the teacher: never charge the student for it.
        _record_outcome(
            submission_id, token, Submission.Status.SYSTEM_ERROR,
            "No test cases configured for this problem.",
        )
        return {"status": Submission.Status.SYSTEM_ERROR}

    try:
        executor = JudgeExecutor()
        outcome = executor.judge_submission_source(
            source_code=submission.source_code,
            test_cases=test_cases,
            time_limit_ms=problem.time_limit_ms,
            memory_limit_mb=problem.memory_limit_mb,
            run_all_tests=problem.run_all_tests,
        )
    except SoftTimeLimitExceeded:
        logger.error("Judging submission %s exceeded the task time limit", submission_id)
        _record_outcome(submission_id, token, Submission.Status.SYSTEM_ERROR, SYSTEM_ERROR_MESSAGE)
        return {"status": Submission.Status.SYSTEM_ERROR, "error": "timeout"}
    except Exception as exc:
        logger.exception("Judge failed for submission %s: %s", submission_id, exc)
        # Once retries run out Celery re-raises `exc` itself, not
        # MaxRetriesExceededError, so check the budget here instead.
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc, args=(submission_id,), kwargs={"claim": str(token)})
        _record_outcome(submission_id, token, Submission.Status.SYSTEM_ERROR, SYSTEM_ERROR_MESSAGE)
        return {"status": Submission.Status.SYSTEM_ERROR, "error": "internal"}

    _record_outcome(
        submission_id, token, outcome["status"],
        outcome.get("compile_error", ""), outcome.get("results", []),
    )
    logger.info("Submission %s judged as %s", submission_id, outcome["status"])
    return {"status": outcome["status"], "results": len(outcome.get("results", []))}


@shared_task
def recover_stuck_submissions() -> dict:
    """Periodic sweep (beat, every minute) that re-queues lost or failed judging.

    - Judging for longer than JUDGE_STALE_SECONDS: the worker died mid-judge.
    - Pending, queued longer ago than that: the broker lost the task.
    - SystemError: an infrastructure failure, retried MAX_AUTO_REJUDGES times.
    Also removes sandbox containers and workspaces orphaned by a crash.
    """
    from submissions.models import Submission, SubmissionResult

    now = timezone.now()
    stale = now - timedelta(seconds=settings.JUDGE_STALE_SECONDS)

    with transaction.atomic():
        stuck = list(
            Submission.objects.select_for_update(skip_locked=True)
            .filter(status=Submission.Status.JUDGING)
            .filter(
                Q(judging_started_at__lt=stale)
                | Q(judging_started_at__isnull=True, submitted_at__lt=stale)
            )
            .values_list("pk", flat=True)
        )
        Submission.objects.filter(pk__in=stuck).update(
            status=Submission.Status.PENDING, judge_claim=None, judging_started_at=None
        )

        lost = list(
            Submission.objects.filter(status=Submission.Status.PENDING)
            .filter(
                Q(enqueued_at__lt=stale)
                | Q(enqueued_at__isnull=True, submitted_at__lt=stale)
            )
            .exclude(pk__in=stuck)
            .values_list("pk", flat=True)
        )

        failed = list(
            Submission.objects.select_for_update(skip_locked=True)
            .filter(
                status=Submission.Status.SYSTEM_ERROR,
                auto_rejudges__lt=MAX_AUTO_REJUDGES,
                judged_at__lt=now - SYSTEM_ERROR_RETRY_AFTER,
            )
            .values_list("pk", flat=True)
        )
        SubmissionResult.objects.filter(submission_id__in=failed).delete()
        Submission.objects.filter(pk__in=failed).update(
            status=Submission.Status.PENDING,
            compile_error="",
            judged_at=None,
            auto_rejudges=F("auto_rejudges") + 1,
        )

    requeue = stuck + lost + failed
    for submission_id in requeue:
        enqueue_judging(submission_id)
    if requeue:
        logger.warning(
            "Recovery sweep re-queued submissions: stuck=%s lost=%s system_error=%s",
            stuck, lost, failed,
        )

    try:
        from judge.executor import JudgeExecutor

        removed = JudgeExecutor().cleanup_orphans(older_than=stale)
    except Exception:
        logger.exception("Sandbox orphan cleanup failed")
        removed = None
    return {"requeued": requeue, "orphans_removed": removed}


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
        # See judge_submission: retry() re-raises `exc` once retries run out.
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc)
        return {
            "status": "SystemError",
            "compile_error": "",
            "stdout": "",
            "stderr": "Internal sandbox error. Please retry.",
            "execution_time_ms": None,
        }
