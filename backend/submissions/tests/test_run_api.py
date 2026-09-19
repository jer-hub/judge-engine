from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from problems.models import Problem, TestCase

User = get_user_model()


class RunPreviewApiTests(APITestCase):
    def setUp(self):
        self.student = User.objects.create_user(
            username="runner",
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
        token = RefreshToken.for_user(self.student).access_token
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def test_run_preview_returns_stdout(self):
        url = reverse("run-preview")
        fake = {
            "status": "OK",
            "compile_error": "",
            "stdout": "3\n",
            "stderr": "",
            "execution_time_ms": 100,
        }
        with patch("judge.tasks.preview_run.delay") as mocked:
            mocked.return_value.get.return_value = fake
            resp = self.client.post(
                url,
                {
                    "problem": self.problem.id,
                    "source_code": "public class Solution { public static void main(String[] a){} }",
                    "language": "java",
                    "stdin": "1 2\n",
                },
                format="json",
            )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["status"], "OK")
        self.assertEqual(resp.data["stdout"], "3\n")
        mocked.assert_called_once()

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
