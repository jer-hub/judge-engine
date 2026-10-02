from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from problems.models import Problem
from submissions.models import Submission

User = get_user_model()


class ProblemListProgressTests(APITestCase):
    def setUp(self):
        self.alice = User.objects.create_user(username="alice", password="pass12345")
        self.bob = User.objects.create_user(username="bob", password="pass12345")
        self.solved = Problem.objects.create(title="A", slug="a", statement="x", is_published=True)
        self.tried = Problem.objects.create(title="B", slug="b", statement="x", is_published=True)
        self.untouched = Problem.objects.create(title="C", slug="c", statement="x", is_published=True)
        for problem, status in (
            (self.solved, Submission.Status.WRONG_ANSWER),
            (self.solved, Submission.Status.ACCEPTED),
            (self.tried, Submission.Status.COMPILE_ERROR),
        ):
            Submission.objects.create(user=self.alice, problem=problem, source_code="x", status=status)

    def _progress(self, user):
        token = RefreshToken.for_user(user).access_token
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        rows = self.client.get("/api/problems/").data["results"]
        return {row["slug"]: row["my_progress"] for row in rows}

    def test_markers_reflect_the_viewers_own_submissions(self):
        self.assertEqual(self._progress(self.alice), {"a": "solved", "b": "attempted", "c": None})
        # Another student's work never shows up as yours.
        self.assertEqual(self._progress(self.bob), {"a": None, "b": None, "c": None})
