from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from problems.models import Problem, TestCase
from submissions.models import Submission

User = get_user_model()


class SubmissionApiTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="teacher",
            password="pass12345",
            role=User.Role.ADMIN,
            is_staff=True,
        )
        self.student = User.objects.create_user(
            username="student1",
            password="pass12345",
            role=User.Role.STUDENT,
        )
        self.problem = Problem.objects.create(
            title="A Plus B",
            slug="a-plus-b",
            statement="Read two integers and print their sum.",
            is_published=True,
            created_by=self.admin,
        )
        TestCase.objects.create(
            problem=self.problem,
            input_data="1 2\n",
            expected_output="3\n",
            is_sample=True,
            order=1,
        )

    def _auth(self, user):
        token = RefreshToken.for_user(user).access_token
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def test_student_can_list_published_problems(self):
        self._auth(self.student)
        url = reverse("problem-list")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(resp.data["count"], 1)

    def test_student_cannot_see_hidden_tests(self):
        TestCase.objects.create(
            problem=self.problem,
            input_data="5 5\n",
            expected_output="10\n",
            is_sample=False,
            order=2,
        )
        self._auth(self.student)
        url = reverse("problem-detail", kwargs={"slug": self.problem.slug})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        samples = resp.data["sample_tests"]
        self.assertEqual(len(samples), 1)
        self.assertEqual(samples[0]["input_data"], "1 2\n")

    def test_create_submission_enqueues_pending(self):
        self._auth(self.student)
        url = reverse("submission-list")
        source = """
import java.util.*;
public class Solution {
  public static void main(String[] args) {
    Scanner sc = new Scanner(System.in);
    System.out.println(sc.nextInt() + sc.nextInt());
  }
}
"""
        # Avoid actually hitting Celery/Docker in unit tests
        from unittest.mock import patch

        with patch("judge.tasks.judge_submission.delay") as mocked:
            resp = self.client.post(
                url,
                {
                    "problem": self.problem.id,
                    "source_code": source,
                    "language": "java",
                },
                format="json",
            )
            self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
            self.assertEqual(resp.data["status"], Submission.Status.PENDING)
            mocked.assert_called_once()

    def test_no_public_register_endpoint(self):
        resp = self.client.post("/api/auth/register/", {"username": "x"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
