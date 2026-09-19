from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from problems.models import Problem
from problems.models import TestCase as ProblemTestCase
from submissions.models import Submission, SubmissionResult

User = get_user_model()


class RoleModelTests(TestCase):
    def test_staff_student_is_not_platform_admin(self):
        user = User.objects.create_user(
            username="staffstu",
            password="x",
            role=User.Role.STUDENT,
            is_staff=True,
        )
        self.assertFalse(user.is_platform_admin)

    def test_admin_role_is_platform_admin_and_gets_staff(self):
        user = User.objects.create_user(
            username="teacher",
            password="x",
            role=User.Role.ADMIN,
        )
        user.refresh_from_db()
        self.assertTrue(user.is_platform_admin)
        self.assertTrue(user.is_staff)

    def test_me_exposes_is_platform_admin(self):
        user = User.objects.create_user(
            username="meuser",
            password="pass12345",
            role=User.Role.STUDENT,
        )
        token = RefreshToken.for_user(user).access_token
        api = APIClient()
        api.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        resp = api.get(reverse("auth-me"))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn("is_platform_admin", resp.data)
        self.assertFalse(resp.data["is_platform_admin"])


class SubmissionResultVisibilityTests(APITestCase):
    def setUp(self):
        self.student = User.objects.create_user(
            username="vis_student",
            password="pass12345",
            role=User.Role.STUDENT,
        )
        self.admin = User.objects.create_user(
            username="vis_admin",
            password="pass12345",
            role=User.Role.ADMIN,
            is_staff=True,
        )
        self.problem = Problem.objects.create(
            title="P",
            slug="vis-p",
            statement="x",
            is_published=True,
        )
        sample = ProblemTestCase.objects.create(
            problem=self.problem,
            input_data="1\n",
            expected_output="1\n",
            is_sample=True,
            order=1,
        )
        hidden = ProblemTestCase.objects.create(
            problem=self.problem,
            input_data="2\n",
            expected_output="2\n",
            is_sample=False,
            order=2,
        )
        self.submission = Submission.objects.create(
            user=self.student,
            problem=self.problem,
            source_code="x",
            status=Submission.Status.ACCEPTED,
        )
        SubmissionResult.objects.create(
            submission=self.submission,
            test_case=sample,
            verdict=Submission.Status.ACCEPTED,
        )
        SubmissionResult.objects.create(
            submission=self.submission,
            test_case=hidden,
            verdict=Submission.Status.ACCEPTED,
        )

    def test_student_only_sees_sample_results(self):
        token = RefreshToken.for_user(self.student).access_token
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        resp = self.client.get(
            reverse("submission-detail", kwargs={"pk": self.submission.pk})
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data["results"]), 1)
        self.assertTrue(resp.data["results"][0]["is_sample"])

    def test_admin_sees_all_results(self):
        token = RefreshToken.for_user(self.admin).access_token
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        resp = self.client.get(
            reverse("submission-detail", kwargs={"pk": self.submission.pk})
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data["results"]), 2)


class SeedDemoPasswordTests(TestCase):
    def test_seed_does_not_reset_existing_student_password(self):
        from django.core.management import call_command

        call_command("seed_demo", force=True)
        user = User.objects.get(username="alice")
        user.set_password("custom-pass-99")
        user.save()
        call_command("seed_demo", force=True)
        user.refresh_from_db()
        self.assertTrue(user.check_password("custom-pass-99"))

    def test_seed_reset_passwords_flag(self):
        from django.core.management import call_command

        call_command("seed_demo", force=True)
        user = User.objects.get(username="alice")
        user.set_password("custom-pass-99")
        user.save()
        call_command("seed_demo", force=True, reset_passwords=True)
        user.refresh_from_db()
        self.assertTrue(user.check_password("demo123"))


class BootstrapAdminTests(TestCase):
    def test_rejects_weak_password(self):
        from django.core.management import call_command
        from django.core.management.base import CommandError

        with self.assertRaises(CommandError):
            call_command("bootstrap_admin", username="newadmin", password="admin123")
