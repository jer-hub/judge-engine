from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from problems.models import Problem, TestCase
from submissions.models import Submission, SubmissionResult

User = get_user_model()


class NestedTestCaseApiTests(APITestCase):
    """PATCH /problems/<slug>/ with test_cases must update cases in place by id."""

    def setUp(self):
        self.admin = User.objects.create_user(
            username="teacher", password="x", role=User.Role.ADMIN
        )
        self.problem = Problem.objects.create(
            title="Sum", slug="sum", statement="x", is_published=True
        )
        self.tc1 = TestCase.objects.create(
            problem=self.problem, input_data="1 2\n", expected_output="3\n", order=1
        )
        self.tc2 = TestCase.objects.create(
            problem=self.problem, input_data="2 2\n", expected_output="4\n", order=2
        )
        sub = Submission.objects.create(
            user=self.admin, problem=self.problem, source_code="x",
            status=Submission.Status.ACCEPTED,
        )
        self.result = SubmissionResult.objects.create(
            submission=sub, test_case=self.tc1, verdict=Submission.Status.ACCEPTED
        )
        token = RefreshToken.for_user(self.admin).access_token
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def _patch(self, cases):
        return self.client.patch(
            f"/api/problems/{self.problem.slug}/", {"test_cases": cases}, format="json"
        )

    def test_edit_by_id_keeps_case_and_submission_history(self):
        resp = self._patch([
            {"id": self.tc1.id, "order": 1, "input_data": "1 2\n", "expected_output": "3\n"},
            {"id": self.tc2.id, "order": 2, "input_data": "5 5\n", "expected_output": "10\n"},
        ])
        self.assertEqual(resp.status_code, 200, resp.content)
        ids = set(self.problem.test_cases.values_list("id", flat=True))
        self.assertEqual(ids, {self.tc1.id, self.tc2.id})
        self.tc2.refresh_from_db()
        self.assertEqual(self.tc2.expected_output.strip(), "10")
        self.assertTrue(SubmissionResult.objects.filter(pk=self.result.pk).exists())

    def test_omitted_case_is_deleted_and_new_one_created(self):
        resp = self._patch([
            {"id": self.tc1.id, "order": 1, "input_data": "1 2\n", "expected_output": "3\n"},
            {"order": 3, "input_data": "9 9\n", "expected_output": "18\n"},
        ])
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertFalse(TestCase.objects.filter(pk=self.tc2.id).exists())
        self.assertEqual(self.problem.test_cases.count(), 2)

    def test_foreign_id_is_rejected_atomically(self):
        other = Problem.objects.create(title="Other", slug="other", statement="x")
        foreign = TestCase.objects.create(
            problem=other, input_data="0\n", expected_output="0\n", order=1
        )
        resp = self._patch([
            {"order": 9, "input_data": "new\n", "expected_output": "new\n"},
            {"id": foreign.id, "order": 1, "input_data": "x", "expected_output": "x"},
        ])
        self.assertEqual(resp.status_code, 400)
        # Nothing from the failed request was kept.
        self.assertEqual(
            set(self.problem.test_cases.values_list("id", flat=True)),
            {self.tc1.id, self.tc2.id},
        )
