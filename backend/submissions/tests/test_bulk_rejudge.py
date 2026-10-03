from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from contests.models import Contest
from problems.models import Problem
from problems.models import TestCase as ProblemTestCase
from submissions.models import Submission, SubmissionResult
from submissions.rejudge import INLINE_ENQUEUE_MAX

User = get_user_model()
URL = "/api/submissions/bulk-rejudge/"


class BulkRejudgeTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="teacher", password="pass12345", role=User.Role.ADMIN
        )
        self.student = User.objects.create_user(username="stu", password="pass12345")
        self.problem = Problem.objects.create(title="P", slug="p", statement="x", is_published=True)
        self.other = Problem.objects.create(title="Q", slug="q", statement="x", is_published=True)
        self.tc = ProblemTestCase.objects.create(problem=self.problem, input_data="", expected_output="1")
        now = timezone.now()
        self.contest = Contest.objects.create(title="C", start_time=now, end_time=now)

    def _sub(self, status, problem=None, contest=None):
        sub = Submission.objects.create(
            user=self.student, problem=problem or self.problem, contest=contest,
            source_code="x", status=status, judged_at=timezone.now(),
        )
        if status not in (Submission.Status.PENDING, Submission.Status.JUDGING):
            SubmissionResult.objects.create(submission=sub, test_case=self.tc, verdict=status)
        return sub

    def _as(self, user):
        token = RefreshToken.for_user(user).access_token
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def test_rejudges_finished_submissions_of_a_problem(self):
        wa = self._sub(Submission.Status.WRONG_ANSWER)
        ac = self._sub(Submission.Status.ACCEPTED)
        judging = self._sub(Submission.Status.JUDGING)
        elsewhere = self._sub(Submission.Status.WRONG_ANSWER, problem=self.other)
        self._as(self.admin)
        with patch("judge.tasks.judge_submission.delay") as delay:
            resp = self.client.post(URL, {"problem": self.problem.id}, format="json")
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(resp.data, {"queued": 2, "skipped_in_flight": 1})
        self.assertEqual({c.args[0] for c in delay.call_args_list}, {wa.id, ac.id})
        for sub in (wa, ac):
            sub.refresh_from_db()
            self.assertEqual(sub.status, Submission.Status.PENDING)
            self.assertIsNone(sub.judged_at)
            self.assertFalse(sub.results.exists())
        judging.refresh_from_db()
        elsewhere.refresh_from_db()
        self.assertEqual(judging.status, Submission.Status.JUDGING)
        self.assertEqual(elsewhere.status, Submission.Status.WRONG_ANSWER)

    def test_large_batch_is_enqueued_by_a_task_not_the_request(self):
        subs = [self._sub(Submission.Status.ACCEPTED) for _ in range(INLINE_ENQUEUE_MAX + 1)]
        self._as(self.admin)
        with patch("judge.tasks.judge_submission.delay") as delay, \
                patch("judge.tasks.enqueue_judging_many.delay") as many:
            resp = self.client.post(URL, {"problem": self.problem.id}, format="json")
        self.assertEqual(resp.data["queued"], len(subs))
        delay.assert_not_called()
        self.assertEqual(sorted(many.call_args.args[0]), sorted(s.id for s in subs))
        # Marked as queued, so the recovery sweep leaves them alone meanwhile.
        self.assertFalse(Submission.objects.filter(enqueued_at__isnull=True).exists())

    def test_contest_scope(self):
        in_contest = self._sub(Submission.Status.WRONG_ANSWER, contest=self.contest)
        practice = self._sub(Submission.Status.WRONG_ANSWER)
        self._as(self.admin)
        with patch("judge.tasks.judge_submission.delay") as delay:
            resp = self.client.post(URL, {"contest": self.contest.id}, format="json")
        self.assertEqual(resp.data["queued"], 1)
        delay.assert_called_once_with(in_contest.id)
        practice.refresh_from_db()
        self.assertEqual(practice.status, Submission.Status.WRONG_ANSWER)

    def test_requires_a_scope_and_integer_ids(self):
        self._as(self.admin)
        self.assertEqual(self.client.post(URL, {}, format="json").status_code, 400)
        self.assertEqual(self.client.post(URL, {"problem": "abc"}, format="json").status_code, 400)

    def test_students_cannot_bulk_rejudge(self):
        self._as(self.student)
        resp = self.client.post(URL, {"problem": self.problem.id}, format="json")
        self.assertEqual(resp.status_code, 403)

    def test_malformed_list_filter_is_400_not_500(self):
        self._as(self.admin)
        self.assertEqual(self.client.get("/api/submissions/?problem=abc").status_code, 400)
        self.assertEqual(self.client.get("/api/submissions/?contest=1x").status_code, 400)
