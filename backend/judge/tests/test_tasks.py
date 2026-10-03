import itertools
import uuid
from datetime import timedelta
from unittest.mock import patch

from celery.exceptions import SoftTimeLimitExceeded
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone

from judge.executor import CompileTimeout, SandboxError
from judge.tasks import (
    COMPILE_TIMEOUT_MESSAGE,
    MAX_AUTO_REJUDGES,
    SYSTEM_ERROR_MESSAGE,
    TASK_TIME_LIMIT_MESSAGE,
    _record_outcome,
    enqueue_judging,
    judge_submission,
    recover_stuck_submissions,
)
from problems.models import Problem
from problems.models import TestCase as ProblemTestCase
from submissions.models import Submission

User = get_user_model()
_seq = itertools.count()

ACCEPTED = {"status": "Accepted", "compile_error": "", "results": []}


def _submission(status=Submission.Status.PENDING, with_tests=True, **fields):
    n = next(_seq)
    user = User.objects.create_user(username=f"s{n}", password="pass12345")
    problem = Problem.objects.create(
        title=f"P{n}", slug=f"p{n}", statement="x", is_published=True
    )
    if with_tests:
        ProblemTestCase.objects.create(problem=problem, input_data="1\n", expected_output="1\n")
    return Submission.objects.create(
        user=user, problem=problem, source_code="class Solution {}", status=status, **fields
    )


def _age(submission, **delta):
    """Backdate auto_now_add/timestamps, which create() cannot set."""
    ago = timezone.now() - timedelta(**delta)
    Submission.objects.filter(pk=submission.pk).update(submitted_at=ago)
    return ago


@patch("judge.executor.JudgeExecutor")
class JudgeTaskTests(TestCase):
    def test_sandbox_failure_after_retries_is_system_error(self, executor_cls):
        executor_cls.return_value.judge_submission_source.side_effect = SandboxError("down")
        sub = _submission()
        judge_submission.apply(args=[sub.id])
        sub.refresh_from_db()
        self.assertEqual(sub.status, Submission.Status.SYSTEM_ERROR)
        self.assertEqual(sub.compile_error, SYSTEM_ERROR_MESSAGE)
        self.assertIsNone(sub.judge_claim)
        # First attempt plus max_retries retries, all on the same claim.
        self.assertEqual(
            executor_cls.return_value.judge_submission_source.call_count,
            judge_submission.max_retries + 1,
        )

    def test_retry_that_succeeds_records_the_verdict(self, executor_cls):
        executor_cls.return_value.judge_submission_source.side_effect = [
            SandboxError("blip"), ACCEPTED,
        ]
        sub = _submission()
        judge_submission.apply(args=[sub.id])
        sub.refresh_from_db()
        self.assertEqual(sub.status, Submission.Status.ACCEPTED)

    def test_problem_without_test_cases_is_system_error(self, executor_cls):
        sub = _submission(with_tests=False)
        judge_submission.apply(args=[sub.id]).get()
        sub.refresh_from_db()
        self.assertEqual(sub.status, Submission.Status.SYSTEM_ERROR)
        executor_cls.assert_not_called()

    def test_task_time_limit_is_tle_with_partial_results(self, executor_cls):
        sub = _submission()
        case = sub.problem.test_cases.get()

        def run_one_test_then_time_out(**kwargs):
            kwargs["results"].append(
                {"test_case_id": case.id, "verdict": "TimeLimitExceeded", "execution_time_ms": None}
            )
            raise SoftTimeLimitExceeded()

        executor_cls.return_value.judge_submission_source.side_effect = run_one_test_then_time_out
        judge_submission.apply(args=[sub.id]).get()
        sub.refresh_from_db()
        self.assertEqual(sub.status, Submission.Status.TIME_LIMIT_EXCEEDED)
        self.assertEqual(sub.compile_error, TASK_TIME_LIMIT_MESSAGE)
        self.assertEqual(sub.results.count(), 1)
        # The student's verdict, not an infrastructure failure: never re-run.
        with patch("judge.tasks.judge_submission.delay") as delay:
            recover_stuck_submissions()
        delay.assert_not_called()

    def test_compile_timeout_is_compile_error_without_retry(self, executor_cls):
        executor_cls.return_value.judge_submission_source.side_effect = CompileTimeout()
        sub = _submission()
        judge_submission.apply(args=[sub.id]).get()
        sub.refresh_from_db()
        self.assertEqual(sub.status, Submission.Status.COMPILE_ERROR)
        self.assertEqual(sub.compile_error, COMPILE_TIMEOUT_MESSAGE)
        self.assertEqual(executor_cls.return_value.judge_submission_source.call_count, 1)

    def test_rejudge_during_judging_discards_the_old_verdict(self, executor_cls):
        sub = _submission()

        def judge_while_admin_rejudges(**_kwargs):
            # The admin force-rejudges while this task is still running.
            Submission.objects.filter(pk=sub.pk).update(
                status=Submission.Status.PENDING, judge_claim=None, judging_started_at=None
            )
            return ACCEPTED

        executor_cls.return_value.judge_submission_source.side_effect = judge_while_admin_rejudges
        judge_submission.apply(args=[sub.id]).get()
        sub.refresh_from_db()
        self.assertEqual(sub.status, Submission.Status.PENDING)
        self.assertFalse(sub.results.exists())


class RecordOutcomeTests(TestCase):
    def test_only_the_claim_holder_can_write(self):
        claim = uuid.uuid4()
        sub = _submission(status=Submission.Status.JUDGING, judge_claim=claim)
        self.assertFalse(_record_outcome(sub.id, uuid.uuid4(), Submission.Status.ACCEPTED))
        sub.refresh_from_db()
        self.assertEqual(sub.status, Submission.Status.JUDGING)

        self.assertTrue(_record_outcome(sub.id, claim, Submission.Status.ACCEPTED))
        sub.refresh_from_db()
        self.assertEqual(sub.status, Submission.Status.ACCEPTED)
        self.assertIsNone(sub.judge_claim)
        self.assertIsNotNone(sub.judged_at)


class TestCaseDeletedMidJudgeTests(TestCase):
    def test_verdict_for_a_deleted_case_requeues_instead_of_failing(self):
        sub = _submission(status=Submission.Status.JUDGING)
        token = uuid.uuid4()
        Submission.objects.filter(pk=sub.pk).update(judge_claim=token)
        case = sub.problem.test_cases.get()
        results = [{"test_case_id": case.id, "verdict": "Accepted"}]
        case.delete()  # a teacher edits the problem mid-judge
        with patch("judge.tasks.judge_submission.delay") as delay, \
                self.captureOnCommitCallbacks(execute=True):
            written = _record_outcome(sub.id, token, "Accepted", "", results)
        self.assertFalse(written)
        sub.refresh_from_db()
        self.assertEqual(sub.status, Submission.Status.PENDING)
        self.assertIsNone(sub.judge_claim)
        delay.assert_called_once_with(sub.id)


class EnqueueTests(TestCase):
    def test_broker_down_keeps_submission_pending(self):
        sub = _submission()
        with patch("judge.tasks.judge_submission.delay", side_effect=ConnectionError("redis down")):
            self.assertFalse(enqueue_judging(sub.id))
        sub.refresh_from_db()
        self.assertEqual(sub.status, Submission.Status.PENDING)
        self.assertIsNotNone(sub.enqueued_at)


@override_settings(JUDGE_STALE_SECONDS=60)
@patch("judge.executor.JudgeExecutor")
@patch("judge.tasks.judge_submission.delay")
class RecoverySweepTests(TestCase):
    def test_stuck_judging_is_reset_and_requeued(self, delay, _executor_cls):
        old = timezone.now() - timedelta(minutes=5)
        stuck = _submission(
            status=Submission.Status.JUDGING, judge_claim=uuid.uuid4(), judging_started_at=old
        )
        busy = _submission(
            status=Submission.Status.JUDGING, judge_claim=uuid.uuid4(),
            judging_started_at=timezone.now(),
        )
        recover_stuck_submissions.apply().get()
        stuck.refresh_from_db()
        busy.refresh_from_db()
        self.assertEqual(stuck.status, Submission.Status.PENDING)
        self.assertIsNone(stuck.judge_claim)
        self.assertEqual(busy.status, Submission.Status.JUDGING)
        delay.assert_called_once_with(stuck.id)

    def test_lost_pending_is_requeued(self, delay, _executor_cls):
        lost = _submission(enqueued_at=timezone.now() - timedelta(minutes=5))
        never_queued = _submission()
        _age(never_queued, minutes=5)
        fresh = _submission(enqueued_at=timezone.now())
        recover_stuck_submissions.apply().get()
        requeued = {c.args[0] for c in delay.call_args_list}
        self.assertEqual(requeued, {lost.id, never_queued.id})
        self.assertNotIn(fresh.id, requeued)

    def test_system_error_is_retried_up_to_the_cap(self, delay, _executor_cls):
        judged = timezone.now() - timedelta(minutes=5)
        retry = _submission(status=Submission.Status.SYSTEM_ERROR, judged_at=judged)
        capped = _submission(
            status=Submission.Status.SYSTEM_ERROR, judged_at=judged,
            auto_rejudges=MAX_AUTO_REJUDGES,
        )
        just_failed = _submission(status=Submission.Status.SYSTEM_ERROR, judged_at=timezone.now())
        recover_stuck_submissions.apply().get()
        retry.refresh_from_db()
        capped.refresh_from_db()
        just_failed.refresh_from_db()
        self.assertEqual(retry.status, Submission.Status.PENDING)
        self.assertEqual(retry.auto_rejudges, 1)
        self.assertEqual(capped.status, Submission.Status.SYSTEM_ERROR)
        self.assertEqual(just_failed.status, Submission.Status.SYSTEM_ERROR)
        delay.assert_called_once_with(retry.id)

    def test_finished_submissions_are_left_alone(self, delay, _executor_cls):
        done = _submission(status=Submission.Status.WRONG_ANSWER, judged_at=timezone.now())
        _age(done, hours=2)
        recover_stuck_submissions.apply().get()
        delay.assert_not_called()

    def test_orphan_cleanup_failure_does_not_break_the_sweep(self, delay, executor_cls):
        executor_cls.return_value.cleanup_orphans.side_effect = RuntimeError("no docker")
        lost = _submission(enqueued_at=timezone.now() - timedelta(minutes=5))
        result = recover_stuck_submissions.apply().get()
        self.assertEqual(result["requeued"], [lost.id])
        self.assertIsNone(result["orphans_removed"])
