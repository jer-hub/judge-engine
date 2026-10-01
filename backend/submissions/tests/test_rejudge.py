from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase as DjangoTestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from judge.tasks import judge_submission
from problems.models import Problem, TestCase
from submissions.models import Submission

User = get_user_model()


def _make_submission(status_value):
    student = User.objects.create_user(
        username="student1", password="pass12345", role=User.Role.STUDENT
    )
    problem = Problem.objects.create(
        title="A Plus B", slug="a-plus-b", statement="sum", is_published=True
    )
    TestCase.objects.create(
        problem=problem, input_data="1 2\n", expected_output="3\n", order=1
    )
    return Submission.objects.create(
        user=student, problem=problem, source_code="class Solution {}",
        status=status_value,
    )


class RejudgeApiTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="teacher", password="pass12345", role=User.Role.ADMIN
        )
        token = RefreshToken.for_user(self.admin).access_token
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def test_rejudge_in_flight_is_conflict(self):
        sub = _make_submission(Submission.Status.JUDGING)
        with patch("judge.tasks.judge_submission.delay") as mocked:
            resp = self.client.post(reverse("submission-rejudge", args=[sub.id]))
        self.assertEqual(resp.status_code, status.HTTP_409_CONFLICT)
        mocked.assert_not_called()

    def test_force_rejudge_recovers_stuck_submission(self):
        sub = _make_submission(Submission.Status.JUDGING)
        with patch("judge.tasks.judge_submission.delay") as mocked:
            resp = self.client.post(
                reverse("submission-rejudge", args=[sub.id]) + "?force=true"
            )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        mocked.assert_called_once_with(sub.id)

    def test_rejudge_finished_submission(self):
        sub = _make_submission(Submission.Status.WRONG_ANSWER)
        with patch("judge.tasks.judge_submission.delay") as mocked:
            resp = self.client.post(reverse("submission-rejudge", args=[sub.id]))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        sub.refresh_from_db()
        self.assertEqual(sub.status, Submission.Status.PENDING)
        mocked.assert_called_once_with(sub.id)


class JudgeClaimTests(DjangoTestCase):
    OUTCOME = {
        "status": "Accepted",
        "compile_error": "",
        "results": [],
    }

    def test_second_task_skips_submission_already_judging(self):
        sub = _make_submission(Submission.Status.JUDGING)
        with patch("judge.executor.JudgeExecutor") as executor_cls:
            result = judge_submission.apply(args=[sub.id]).get()
        self.assertTrue(result["skipped"])
        executor_cls.assert_not_called()

    def test_pending_submission_is_claimed_and_judged(self):
        sub = _make_submission(Submission.Status.PENDING)
        with patch("judge.executor.JudgeExecutor") as executor_cls:
            executor_cls.return_value.judge_submission_source.return_value = self.OUTCOME
            result = judge_submission.apply(args=[sub.id]).get()
        self.assertEqual(result["status"], "Accepted")
        sub.refresh_from_db()
        self.assertEqual(sub.status, Submission.Status.ACCEPTED)
