from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from problems.models import Problem, TestCase

User = get_user_model()


class _FakeRedis:
    def __init__(self):
        self.store = {}

    def setex(self, key, _ttl, value):
        self.store[key] = str(value)

    def get(self, key):
        return self.store.get(key)


class RunPreviewApiTests(APITestCase):
    def setUp(self):
        self.student = User.objects.create_user(
            username="runner",
            password="pass12345",
            role=User.Role.STUDENT,
        )
        self.other = User.objects.create_user(
            username="snoop",
            password="pass12345",
            role=User.Role.STUDENT,
        )
        self.problem = Problem.objects.create(
            title="Echo Sum",
            slug="echo-sum",
            statement="sum",
            is_published=True,
        )
        TestCase.objects.create(
            problem=self.problem,
            input_data="1 2\n",
            expected_output="3\n",
            is_sample=True,
            order=1,
        )
        self.redis = _FakeRedis()
        patcher = patch(
            "submissions.run_views._redis_client", return_value=self.redis
        )
        patcher.start()
        self.addCleanup(patcher.stop)
        self._login(self.student)

    def _login(self, user):
        token = RefreshToken.for_user(user).access_token
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def _queue(self):
        with patch("judge.tasks.preview_run.apply_async") as mocked:
            mocked.return_value.id = "task-123"
            resp = self.client.post(
                reverse("run-preview"),
                {
                    "problem": self.problem.id,
                    "source_code": "public class Solution { public static void main(String[] a){} }",
                    "language": "java",
                    "stdin": "1 2\n",
                },
                format="json",
            )
        mocked.assert_called_once()
        # A preview nobody waits for any more is dropped, not run.
        self.assertTrue(mocked.call_args.kwargs.get("expires"))
        return resp

    def test_run_preview_queues_without_blocking(self):
        resp = self._queue()
        self.assertEqual(resp.status_code, status.HTTP_202_ACCEPTED)
        self.assertEqual(resp.data, {"task_id": "task-123", "status": "Pending"})

    def test_poll_returns_result_when_done(self):
        self._queue()
        fake = MagicMock(state="SUCCESS", result={
            "status": "OK",
            "compile_error": "",
            "stdout": "3\n",
            "stderr": "",
            "execution_time_ms": 100,
        })
        with patch("submissions.run_views.AsyncResult", return_value=fake):
            resp = self.client.get(reverse("run-preview-result", args=["task-123"]))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["status"], "OK")
        self.assertEqual(resp.data["stdout"], "3\n")

    def test_poll_reports_pending(self):
        self._queue()
        with patch("submissions.run_views.AsyncResult",
                   return_value=MagicMock(state="STARTED")):
            resp = self.client.get(reverse("run-preview-result", args=["task-123"]))
        self.assertEqual(resp.data["status"], "Running")

    def test_other_user_cannot_read_preview(self):
        self._queue()
        self._login(self.other)
        resp = self.client.get(reverse("run-preview-result", args=["task-123"]))
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_unknown_task_is_404(self):
        resp = self.client.get(reverse("run-preview-result", args=["nope"]))
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_run_rejects_empty_source(self):
        url = reverse("run-preview")
        resp = self.client.post(
            url,
            {
                "problem": self.problem.id,
                "source_code": "   ",
                "language": "java",
                "stdin": "",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
