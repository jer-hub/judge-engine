from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from contests.models import Contest, ContestParticipant, ContestProblem
from contests.scoreboard import build_scoreboard
from problems.models import Problem
from submissions.models import Submission

User = get_user_model()


def _no_cache():
    # Keep the shared Redis scoreboard cache out of these tests.
    return patch("contests.scoreboard._redis_client", side_effect=RuntimeError)


class FreezeTests(APITestCase):
    def setUp(self):
        self.alice = User.objects.create_user(username="alice", password="x")
        self.bob = User.objects.create_user(username="bob", password="x")
        self.admin = User.objects.create_user(
            username="teacher", password="x", role=User.Role.ADMIN
        )
        self.problem = Problem.objects.create(
            title="P", slug="p", statement="x", is_published=True
        )
        now = timezone.now()
        # Frozen for the last 30 minutes; we are 10 minutes from the end.
        self.contest = Contest.objects.create(
            title="Finals",
            start_time=now - timedelta(minutes=110),
            end_time=now + timedelta(minutes=10),
            freeze_scoreboard_minutes_before_end=30,
        )
        ContestProblem.objects.create(
            contest=self.contest, problem=self.problem, letter="A"
        )
        for user in (self.alice, self.bob):
            ContestParticipant.objects.create(contest=self.contest, user=user)
        sub = Submission.objects.create(
            user=self.alice, problem=self.problem, contest=self.contest,
            source_code="x", status=Submission.Status.ACCEPTED,
        )
        Submission.objects.filter(pk=sub.pk).update(submitted_at=now - timedelta(minutes=5))

    def _alice_cell(self, board):
        row = next(r for r in board["standings"] if r["username"] == "alice")
        return row["problems"][0]

    def test_post_freeze_solve_hidden_from_every_student(self):
        with _no_cache():
            for viewer in (self.alice, self.bob):
                cell = self._alice_cell(build_scoreboard(self.contest, viewer=viewer))
                self.assertFalse(cell["solved"], f"leaked to {viewer.username}")
                self.assertTrue(cell["pending"])

    def test_shared_cache_never_holds_a_revealed_board(self):
        store = {}

        class FakeRedis:
            def get(self, key):
                return store.get(key)

            def setex(self, key, _ttl, value):
                store[key] = value

        with patch("contests.scoreboard._redis_client", return_value=FakeRedis()):
            build_scoreboard(self.contest, viewer=self.alice)  # fills the cache
            cell = self._alice_cell(build_scoreboard(self.contest, viewer=self.bob))
        self.assertFalse(cell["solved"])

    def test_admin_sees_through_freeze(self):
        with _no_cache():
            cell = self._alice_cell(build_scoreboard(self.contest, viewer=self.admin))
        self.assertTrue(cell["solved"])


class UpcomingContestVisibilityTests(APITestCase):
    def setUp(self):
        self.student = User.objects.create_user(username="stu", password="x")
        self.admin = User.objects.create_user(
            username="teacher", password="x", role=User.Role.ADMIN
        )
        problem = Problem.objects.create(
            title="Secret Graph Problem", slug="secret", statement="x", is_published=False
        )
        now = timezone.now()
        self.contest = Contest.objects.create(
            title="Next week",
            start_time=now + timedelta(days=1),
            end_time=now + timedelta(days=1, hours=2),
            is_public=True,
        )
        ContestProblem.objects.create(contest=self.contest, problem=problem, letter="A")

    def _get(self, user, path):
        token = RefreshToken.for_user(user).access_token
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        return self.client.get(path)

    def test_student_cannot_see_problems_before_start(self):
        resp = self._get(self.student, f"/api/contests/{self.contest.id}/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["problems"], [])
        self.assertNotIn("Secret Graph Problem", resp.content.decode())

    def test_scoreboard_hides_problems_before_start(self):
        with _no_cache():
            resp = self._get(self.student, f"/api/contests/{self.contest.id}/scoreboard/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["problems"], [])
        self.assertNotIn("Secret Graph Problem", resp.content.decode())

    def test_scoreboard_hides_roster_before_start(self):
        ContestParticipant.objects.create(contest=self.contest, user=self.admin)
        with _no_cache():
            resp = self._get(self.student, f"/api/contests/{self.contest.id}/scoreboard/")
        self.assertEqual(resp.data["standings"], [])

    def test_admin_still_sees_problems(self):
        resp = self._get(self.admin, f"/api/contests/{self.contest.id}/")
        self.assertEqual(len(resp.data["problems"]), 1)
