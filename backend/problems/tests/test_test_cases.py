from django.contrib.auth import get_user_model
from django.test import TestCase as DjangoTestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from problems.models import Problem
from problems.models import TestCase as ProblemTestCase
from problems.test_case_sync import reconcile_test_cases
from submissions.models import Submission, SubmissionResult

User = get_user_model()


class TestCaseSyncTests(DjangoTestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="sync_admin",
            password="pass12345",
            role=User.Role.ADMIN,
            is_staff=True,
        )
        self.problem = Problem.objects.create(
            title="Sync Prob",
            slug="sync-prob",
            statement="s",
            created_by=self.admin,
        )
        self.tc1 = ProblemTestCase.objects.create(
            problem=self.problem,
            input_data="1\n",
            expected_output="1\n",
            is_sample=True,
            order=0,
        )
        self.tc2 = ProblemTestCase.objects.create(
            problem=self.problem,
            input_data="2\n",
            expected_output="2\n",
            is_sample=False,
            order=1,
        )
        self.tc3 = ProblemTestCase.objects.create(
            problem=self.problem,
            input_data="3\n",
            expected_output="3\n",
            is_sample=False,
            order=2,
        )
        self.submission = Submission.objects.create(
            user=self.admin,
            problem=self.problem,
            source_code="class Solution {}",
            language="java",
            status=Submission.Status.ACCEPTED,
        )
        SubmissionResult.objects.create(
            submission=self.submission,
            test_case=self.tc1,
            verdict=Submission.Status.ACCEPTED,
        )
        SubmissionResult.objects.create(
            submission=self.submission,
            test_case=self.tc2,
            verdict=Submission.Status.ACCEPTED,
        )
        SubmissionResult.objects.create(
            submission=self.submission,
            test_case=self.tc3,
            verdict=Submission.Status.ACCEPTED,
        )

    def test_update_one_preserves_results(self):
        before = SubmissionResult.objects.count()
        reconcile_test_cases(
            self.problem,
            [
                {
                    "id": self.tc1.id,
                    "order": 0,
                    "input_data": "1\n",
                    "expected_output": "1\n",
                    "is_sample": True,
                    "points": 1,
                },
                {
                    "id": self.tc2.id,
                    "order": 1,
                    "input_data": "22\n",
                    "expected_output": "22\n",
                    "is_sample": False,
                    "points": 2,
                },
                {
                    "id": self.tc3.id,
                    "order": 2,
                    "input_data": "3\n",
                    "expected_output": "3\n",
                    "is_sample": False,
                    "points": 1,
                },
            ],
        )
        self.tc2.refresh_from_db()
        self.assertEqual(self.tc2.expected_output, "22\n")
        self.assertEqual(SubmissionResult.objects.count(), before)

    def test_omit_id_deletes_case(self):
        reconcile_test_cases(
            self.problem,
            [
                {
                    "id": self.tc1.id,
                    "order": 0,
                    "input_data": "1\n",
                    "expected_output": "1\n",
                    "is_sample": True,
                    "points": 1,
                },
                {
                    "id": self.tc2.id,
                    "order": 1,
                    "input_data": "2\n",
                    "expected_output": "2\n",
                    "is_sample": False,
                    "points": 1,
                },
            ],
        )
        self.assertFalse(ProblemTestCase.objects.filter(id=self.tc3.id).exists())
        self.assertEqual(
            SubmissionResult.objects.filter(test_case_id=self.tc3.id).count(), 0
        )

    def test_foreign_id_raises(self):
        other = Problem.objects.create(title="Other", statement="s")
        foreign = ProblemTestCase.objects.create(
            problem=other,
            input_data="x\n",
            expected_output="x\n",
        )
        from rest_framework.exceptions import ValidationError

        with self.assertRaises(ValidationError):
            reconcile_test_cases(
                self.problem,
                [
                    {
                        "id": foreign.id,
                        "order": 0,
                        "input_data": "x\n",
                        "expected_output": "x\n",
                        "is_sample": False,
                        "points": 1,
                    }
                ],
            )


class TestCaseApiTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="tc_admin",
            password="pass12345",
            role=User.Role.ADMIN,
            is_staff=True,
        )
        self.student = User.objects.create_user(
            username="tc_student",
            password="pass12345",
            role=User.Role.STUDENT,
        )
        self.problem = Problem.objects.create(
            title="TC Prob",
            slug="tc-prob",
            statement="s",
            is_published=True,
            created_by=self.admin,
        )
        self.tc = ProblemTestCase.objects.create(
            problem=self.problem,
            input_data="1\n",
            expected_output="secret\n",
            is_sample=False,
            order=0,
        )

    def _auth(self, user):
        token = RefreshToken.for_user(user).access_token
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def test_student_forbidden_list_and_detail(self):
        self._auth(self.student)
        resp = self.client.get(reverse("testcase-list"))
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
        resp = self.client.get(reverse("testcase-detail", kwargs={"pk": self.tc.id}))
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_crud_and_filter(self):
        self._auth(self.admin)
        resp = self.client.get(reverse("testcase-list"), {"problem": self.problem.id})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(resp.data["count"], 1)
        self.assertEqual(resp.data["results"][0]["expected_output"], "secret\n")

        resp = self.client.post(
            reverse("testcase-list"),
            {
                "problem": self.problem.id,
                "input_data": "2\n",
                "expected_output": "2\n",
                "is_sample": True,
                "order": 1,
                "points": 1,
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        new_id = resp.data["id"]

        resp = self.client.patch(
            reverse("testcase-detail", kwargs={"pk": new_id}),
            {"expected_output": "22\n"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        resp = self.client.delete(reverse("testcase-detail", kwargs={"pk": new_id}))
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)

    def test_reorder(self):
        tc2 = ProblemTestCase.objects.create(
            problem=self.problem,
            input_data="2\n",
            expected_output="2\n",
            order=1,
        )
        self._auth(self.admin)
        resp = self.client.post(
            reverse("testcase-reorder"),
            {
                "items": [
                    {"id": self.tc.id, "order": 5},
                    {"id": tc2.id, "order": 0},
                ]
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.tc.refresh_from_db()
        tc2.refresh_from_db()
        self.assertEqual(self.tc.order, 5)
        self.assertEqual(tc2.order, 0)

    def test_delete_problem_with_submissions_conflict(self):
        Submission.objects.create(
            user=self.student,
            problem=self.problem,
            source_code="x",
            language="java",
        )
        self._auth(self.admin)
        resp = self.client.delete(
            reverse("problem-detail", kwargs={"slug": self.problem.slug})
        )
        self.assertEqual(resp.status_code, status.HTTP_409_CONFLICT)
        self.assertTrue(Problem.objects.filter(pk=self.problem.pk).exists())
