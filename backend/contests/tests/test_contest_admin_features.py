from datetime import timedelta

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from contests.models import Contest, ContestParticipant, ContestProblem
from problems.models import Problem
from problems.models import TestCase as ProblemTestCase

User = get_user_model()


class ContestFeaturesTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="c_admin",
            password="pass12345",
            role=User.Role.ADMIN,
            is_staff=True,
        )
        self.student = User.objects.create_user(
            username="c_student",
            password="pass12345",
            role=User.Role.STUDENT,
        )
        self.problem = Problem.objects.create(
            title="Hidden Contest Prob",
            slug="hidden-contest-prob",
            statement="s",
            is_published=False,
            created_by=self.admin,
        )
        ProblemTestCase.objects.create(
            problem=self.problem,
            input_data="1\n",
            expected_output="1\n",
            is_sample=True,
        )
        now = timezone.now()
        self.contest = Contest.objects.create(
            title="Live Cup",
            start_time=now - timedelta(hours=1),
            end_time=now + timedelta(hours=2),
            is_public=True,
            created_by=self.admin,
        )
        ContestProblem.objects.create(
            contest=self.contest,
            problem=self.problem,
            letter="A",
            display_order=0,
        )
        ContestParticipant.objects.create(contest=self.contest, user=self.student)

    def _auth(self, user):
        token = RefreshToken.for_user(user).access_token
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def test_admin_can_set_contest_problems(self):
        self._auth(self.admin)
        published = Problem.objects.create(
            title="Pub",
            slug="pub-cp",
            statement="s",
            is_published=True,
            created_by=self.admin,
        )
        resp = self.client.patch(
            reverse("contest-detail", kwargs={"pk": self.contest.id}),
            {
                "problems": [
                    {
                        "problem_id": self.problem.id,
                        "letter": "A",
                        "display_order": 0,
                        "points": 100,
                    },
                    {
                        "problem_id": published.id,
                        "letter": "B",
                        "display_order": 1,
                        "points": 100,
                    },
                ]
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data["problems"]), 2)

    def test_student_can_retrieve_unpublished_in_active_contest(self):
        self._auth(self.student)
        resp = self.client.get(
            reverse("problem-detail", kwargs={"slug": self.problem.slug})
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_student_can_submit_unpublished_via_contest(self):
        self._auth(self.student)
        from unittest.mock import patch

        with patch("judge.tasks.judge_submission.delay"):
            resp = self.client.post(
                reverse("submission-list"),
                {
                    "problem": self.problem.id,
                    "contest": self.contest.id,
                    "source_code": "public class Solution { public static void main(String[] a){} }",
                    "language": "java",
                },
                format="json",
            )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

    def test_student_cannot_submit_unpublished_without_contest(self):
        self._auth(self.student)
        resp = self.client.post(
            reverse("submission-list"),
            {
                "problem": self.problem.id,
                "source_code": "public class Solution { public static void main(String[] a){} }",
                "language": "java",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)


class RosterApiTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="roster_admin",
            password="pass12345",
            role=User.Role.ADMIN,
            is_staff=True,
        )
        self.student = User.objects.create_user(
            username="roster_stu",
            password="pass12345",
            role=User.Role.STUDENT,
        )

    def _auth(self, user):
        token = RefreshToken.for_user(user).access_token
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def test_student_forbidden(self):
        self._auth(self.student)
        resp = self.client.get(reverse("user-list"))
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_create_and_reset_password(self):
        self._auth(self.admin)
        resp = self.client.post(
            reverse("user-list"),
            {
                "username": "newkid",
                "password": "SecurePass1!",
                "role": "student",
                "class_section": "A1",
                "school_id": "S1",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        user_id = resp.data["id"]
        resp = self.client.post(
            reverse("user-reset-password", kwargs={"pk": user_id}),
            {"password": "AnotherPass1!"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)


class RejudgeApiTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="rj_admin",
            password="pass12345",
            role=User.Role.ADMIN,
            is_staff=True,
        )
        self.student = User.objects.create_user(
            username="rj_stu",
            password="pass12345",
            role=User.Role.STUDENT,
        )
        self.problem = Problem.objects.create(
            title="RJ",
            slug="rj-prob",
            statement="s",
            is_published=True,
            created_by=self.admin,
        )
        from submissions.models import Submission

        self.submission = Submission.objects.create(
            user=self.student,
            problem=self.problem,
            source_code="x",
            language="java",
            status=Submission.Status.WRONG_ANSWER,
        )

    def _auth(self, user):
        token = RefreshToken.for_user(user).access_token
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def test_admin_rejudge(self):
        self._auth(self.admin)
        from unittest.mock import patch

        with patch("judge.tasks.judge_submission.delay") as mocked:
            resp = self.client.post(
                reverse("submission-rejudge", kwargs={"pk": self.submission.id})
            )
            self.assertEqual(resp.status_code, status.HTTP_200_OK)
            self.assertEqual(resp.data["status"], "Pending")
            mocked.assert_called_once()

    def test_student_cannot_rejudge(self):
        self._auth(self.student)
        resp = self.client.post(
            reverse("submission-rejudge", kwargs={"pk": self.submission.id})
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
