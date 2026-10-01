from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase as DjangoTestCase
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from contests.models import Contest, ContestParticipant, ContestProblem
from contests.scoreboard import build_scoreboard
from problems.models import Problem
from problems.models import TestCase as ProblemTestCase
from submissions.models import Submission

User = get_user_model()


def _sub(user, problem, contest, status, minute):
    s = Submission.objects.create(
        user=user, problem=problem, contest=contest, source_code="x", status=status
    )
    Submission.objects.filter(pk=s.pk).update(
        submitted_at=contest.start_time + timedelta(minutes=minute)
    )


class ScoringRuleTests(DjangoTestCase):
    def setUp(self):
        now = timezone.now()
        self.contest = Contest.objects.create(
            title="Cup", start_time=now - timedelta(hours=2), end_time=now + timedelta(hours=1)
        )
        self.p1 = Problem.objects.create(title="A", slug="a", statement="x", is_published=True)
        self.p2 = Problem.objects.create(title="B", slug="b", statement="x", is_published=True)
        for letter, p in (("A", self.p1), ("B", self.p2)):
            ContestProblem.objects.create(contest=self.contest, problem=p, letter=letter)
        self.users = {}
        for name in ("ann", "ben", "cat", "dan"):
            self.users[name] = User.objects.create_user(username=name, password="x")
            ContestParticipant.objects.create(contest=self.contest, user=self.users[name])

    def _board(self):
        with patch("contests.scoreboard._redis_client", side_effect=RuntimeError):
            return {r["username"]: r for r in build_scoreboard(self.contest)["standings"]}

    def test_compile_error_costs_nothing(self):
        _sub(self.users["ann"], self.p1, self.contest, Submission.Status.COMPILE_ERROR, 5)
        _sub(self.users["ann"], self.p1, self.contest, Submission.Status.ACCEPTED, 10)
        ann = self._board()["ann"]
        self.assertEqual(ann["penalty"], 10)
        self.assertEqual(ann["problems"][0]["attempts"], 1)

    def test_ties_broken_by_last_solve_then_shared(self):
        S = Submission.Status
        # ann and ben: 2 solved, penalty 60 each; ann's last solve is earlier.
        _sub(self.users["ann"], self.p1, self.contest, S.ACCEPTED, 20)
        _sub(self.users["ann"], self.p2, self.contest, S.ACCEPTED, 40)
        _sub(self.users["ben"], self.p1, self.contest, S.ACCEPTED, 10)
        _sub(self.users["ben"], self.p2, self.contest, S.ACCEPTED, 50)
        # cat and dan: identical 1 solve at minute 30 -> same rank.
        _sub(self.users["cat"], self.p1, self.contest, S.ACCEPTED, 30)
        _sub(self.users["dan"], self.p1, self.contest, S.ACCEPTED, 30)
        board = self._board()
        self.assertEqual(board["ann"]["rank"], 1)
        self.assertEqual(board["ben"]["rank"], 2)
        self.assertEqual(board["cat"]["rank"], 3)
        self.assertEqual(board["dan"]["rank"], 3)


class ContestAdminPolishTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username="teacher", password="x", role=User.Role.ADMIN)
        self.student = User.objects.create_user(username="stu", password="x")
        now = timezone.now()
        self.contest = Contest.objects.create(
            title="Cup", start_time=now - timedelta(hours=1), end_time=now + timedelta(hours=1)
        )
        self.pa = Problem.objects.create(title="PA", slug="pa", statement="x", is_published=True)
        self.pb = Problem.objects.create(title="PB", slug="pb", statement="x", is_published=True)
        ContestProblem.objects.create(contest=self.contest, problem=self.pa, letter="A")
        ContestProblem.objects.create(contest=self.contest, problem=self.pb, letter="B")
        ContestParticipant.objects.create(contest=self.contest, user=self.student)

    def _as(self, user):
        token = RefreshToken.for_user(user).access_token
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def _set_problems(self, items):
        return self.client.patch(
            f"/api/contests/{self.contest.id}/", {"problems": items}, format="json"
        )

    def test_swapping_letters_works(self):
        self._as(self.admin)
        resp = self._set_problems([
            {"problem_id": self.pa.id, "letter": "B"},
            {"problem_id": self.pb.id, "letter": "A"},
        ])
        self.assertEqual(resp.status_code, 200, resp.content)
        letters = dict(
            ContestProblem.objects.filter(contest=self.contest).values_list("problem__slug", "letter")
        )
        self.assertEqual(letters, {"pa": "B", "pb": "A"})

    def test_new_problem_can_take_removed_letter(self):
        pc = Problem.objects.create(title="PC", slug="pc", statement="x", is_published=True)
        self._as(self.admin)
        resp = self._set_problems([
            {"problem_id": self.pa.id, "letter": "A"},
            {"problem_id": pc.id, "letter": "B"},
        ])
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertFalse(ContestProblem.objects.filter(contest=self.contest, problem=self.pb).exists())

    def test_freeze_longer_than_contest_rejected(self):
        self._as(self.admin)
        resp = self.client.patch(
            f"/api/contests/{self.contest.id}/",
            {"freeze_scoreboard_minutes_before_end": 120},
            format="json",
        )
        self.assertEqual(resp.status_code, 400)
        ok = self.client.patch(
            f"/api/contests/{self.contest.id}/",
            {"freeze_scoreboard_minutes_before_end": 30},
            format="json",
        )
        self.assertEqual(ok.status_code, 200)

    def test_students_get_participant_count_not_roster(self):
        self._as(self.student)
        data = self.client.get(f"/api/contests/{self.contest.id}/").data
        self.assertNotIn("participants", data)
        self.assertEqual(data["participant_count"], 1)
        self._as(self.admin)
        self.assertEqual(len(self.client.get(f"/api/contests/{self.contest.id}/").data["participants"]), 1)

    def test_non_numeric_test_case_order_is_400(self):
        tc = ProblemTestCase.objects.create(problem=self.pa, input_data="1", expected_output="1")
        self._as(self.admin)
        resp = self.client.post(
            "/api/test-cases/reorder/", {"items": [{"id": tc.id, "order": "abc"}]}, format="json"
        )
        self.assertEqual(resp.status_code, 400)
