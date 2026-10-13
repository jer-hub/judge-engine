from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from contests.models import Contest, ContestParticipant, ContestProblem
from problems.models import Problem
from problems.models import TestCase as ProblemTestCase

User = get_user_model()


class ContestProblemVisibilityTests(APITestCase):
    """A published problem in a contest that isn't over is reached only
    through the contest: not in the public list, statement or practice."""

    def setUp(self):
        self.admin = User.objects.create_user(username="t", password="pass12345", role=User.Role.ADMIN)
        self.player = User.objects.create_user(username="player", password="pass12345")
        self.outsider = User.objects.create_user(username="outsider", password="pass12345")
        self.problem = Problem.objects.create(title="Toy", slug="toy", statement="x", is_published=True)
        self.free = Problem.objects.create(title="Free", slug="free", statement="x", is_published=True)
        for p in (self.problem, self.free):
            ProblemTestCase.objects.create(problem=p, input_data="", expected_output="1")
        now = timezone.now()
        self.contest = Contest.objects.create(
            title="Quiz", start_time=now - timedelta(minutes=10), end_time=now + timedelta(minutes=50)
        )
        ContestProblem.objects.create(contest=self.contest, problem=self.problem, letter="A")
        ContestParticipant.objects.create(contest=self.contest, user=self.player)

    def _as(self, user):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(user).access_token}")

    def _slugs(self, user):
        self._as(user)
        return {p["slug"] for p in self.client.get("/api/problems/").data["results"]}

    def _statement(self, user):
        self._as(user)
        return self.client.get(f"/api/problems/{self.problem.slug}/").status_code

    def _run(self, user):
        self._as(user)
        with patch("judge.tasks.preview_run.apply_async") as run:
            run.return_value.id = "t1"
            return self.client.post(
                "/api/runs/",
                {"problem": self.problem.id, "source_code": "class Solution {}", "language": "java"},
                format="json",
            ).status_code

    def test_hidden_from_the_public_list_while_running(self):
        for user in (self.player, self.outsider):
            self.assertEqual(self._slugs(user), {"free"})
        self.assertEqual(self._slugs(self.admin), {"free", "toy"})

    def test_statement_only_through_the_contest(self):
        self.assertEqual(self._statement(self.player), 200)  # registered, contest running
        self.assertEqual(self._statement(self.outsider), 404)
        self.assertEqual(self._run(self.player), 202)
        self.assertEqual(self._run(self.outsider), 400)

    def test_outsider_practice_submission_says_why(self):
        self._as(self.outsider)
        resp = self.client.post(
            "/api/submissions/",
            {"problem": self.problem.id, "source_code": "class Solution {}", "language": "java"},
            format="json",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("contest that hasn't ended", str(resp.data["problem"]))

    def test_upcoming_contest_hides_it_too(self):
        now = timezone.now()
        Contest.objects.filter(pk=self.contest.pk).update(
            start_time=now + timedelta(days=1), end_time=now + timedelta(days=1, hours=1)
        )
        self.assertEqual(self._slugs(self.outsider), {"free"})
        self.assertEqual(self._statement(self.player), 404)  # not started yet

    def test_back_in_the_public_set_after_the_contest(self):
        now = timezone.now()
        Contest.objects.filter(pk=self.contest.pk).update(end_time=now - timedelta(minutes=1))
        self.assertEqual(self._slugs(self.outsider), {"free", "toy"})
        self.assertEqual(self._statement(self.outsider), 200)

    def test_time_extension_keeps_it_hidden(self):
        now = timezone.now()
        Contest.objects.filter(pk=self.contest.pk).update(end_time=now - timedelta(minutes=1))
        ContestParticipant.objects.filter(contest=self.contest, user=self.player).update(extra_minutes=30)
        self.assertEqual(self._slugs(self.outsider), {"free"})
        self.assertEqual(self._statement(self.player), 200)
