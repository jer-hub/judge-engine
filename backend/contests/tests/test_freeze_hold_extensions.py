from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from contests.access import user_can_access_unpublished_problem
from contests.models import Contest, ContestParticipant, ContestProblem
from contests.scoreboard import build_scoreboard
from problems.models import Problem
from problems.models import TestCase as ProblemTestCase
from submissions.models import Submission

User = get_user_model()


class ContestTestBase(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="teacher", password="pass12345", role=User.Role.ADMIN
        )
        self.alice = User.objects.create_user(username="alice", password="pass12345")
        self.bob = User.objects.create_user(username="bob", password="pass12345")
        # Unpublished: reachable only through the contest window.
        self.problem = Problem.objects.create(title="P", slug="p", statement="x", is_published=False)
        ProblemTestCase.objects.create(problem=self.problem, input_data="", expected_output="1")

    def _contest(self, start_ago, end_ago, **fields):
        now = timezone.now()
        contest = Contest.objects.create(
            title="Quiz", start_time=now - start_ago, end_time=now - end_ago, **fields
        )
        ContestProblem.objects.create(contest=contest, problem=self.problem, letter="A")
        for user in (self.alice, self.bob):
            ContestParticipant.objects.create(contest=contest, user=user)
        return contest

    def _solve(self, contest, user, minutes_after_start):
        sub = Submission.objects.create(
            user=user, problem=self.problem, contest=contest, source_code="x",
            status=Submission.Status.ACCEPTED,
        )
        Submission.objects.filter(pk=sub.pk).update(
            submitted_at=contest.start_time + timedelta(minutes=minutes_after_start)
        )

    def _as(self, user):
        token = RefreshToken.for_user(user).access_token
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")


class HoldResultsTests(ContestTestBase):
    def _ended_contest(self, **fields):
        # 60-minute contest that ended 5 minutes ago, frozen for its last 20.
        contest = self._contest(
            timedelta(minutes=65), timedelta(minutes=5),
            freeze_scoreboard_minutes_before_end=20, **fields,
        )
        self._solve(contest, self.alice, 10)  # before the freeze
        self._solve(contest, self.bob, 50)  # during the freeze
        return contest

    def _solved(self, contest, viewer=None):
        board = build_scoreboard(contest, viewer=viewer)
        return {row["username"]: row["solved"] for row in board["standings"]}

    def test_freeze_lifts_at_the_end_by_default(self):
        contest = self._ended_contest()
        self.assertFalse(contest.is_frozen)
        self.assertEqual(self._solved(contest), {"alice": 1, "bob": 1})

    def test_freeze_holds_while_a_time_extension_runs(self):
        contest = self._ended_contest()
        participant = ContestParticipant.objects.get(contest=contest, user=self.alice)
        participant.extra_minutes = 30  # alice is still competing
        participant.save()
        self.assertTrue(contest.is_frozen)
        self.assertEqual(self._solved(contest), {"alice": 1, "bob": 0})
        # Once the longest extension is over, the freeze lifts.
        participant.extra_minutes = 3
        participant.save()
        self.assertFalse(contest.is_frozen)

    def test_held_results_stay_frozen_until_revealed(self):
        contest = self._ended_contest(hold_results_until_revealed=True)
        self.assertTrue(contest.is_frozen)
        self.assertEqual(self._solved(contest), {"alice": 1, "bob": 0})
        # Admins always see the real standings.
        self.assertEqual(self._solved(contest, viewer=self.admin), {"alice": 1, "bob": 1})

        self._as(self.admin)
        resp = self.client.post(f"/api/contests/{contest.id}/reveal/", {"revealed": True}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.data["is_frozen"])
        contest.refresh_from_db()
        self.assertEqual(self._solved(contest), {"alice": 1, "bob": 1})

        resp = self.client.post(f"/api/contests/{contest.id}/reveal/", {"revealed": False}, format="json")
        self.assertTrue(resp.data["is_frozen"])

    def test_hold_without_freeze_window_freezes_at_the_end(self):
        contest = self._contest(
            timedelta(minutes=65), timedelta(minutes=5), hold_results_until_revealed=True
        )
        self.assertEqual(contest.freeze_at, contest.end_time)
        self.assertTrue(contest.is_frozen)

    def test_only_admins_reveal(self):
        contest = self._ended_contest(hold_results_until_revealed=True)
        self._as(self.alice)
        self.assertEqual(self.client.post(f"/api/contests/{contest.id}/reveal/").status_code, 403)


class TimeExtensionTests(ContestTestBase):
    def setUp(self):
        super().setUp()
        # Ended 10 minutes ago; alice gets 30 extra minutes.
        self.contest = self._contest(timedelta(minutes=70), timedelta(minutes=10))
        ContestParticipant.objects.filter(contest=self.contest, user=self.alice).update(extra_minutes=30)

    def _submit(self, user):
        self._as(user)
        with patch("judge.tasks.judge_submission.delay"):
            return self.client.post(
                "/api/submissions/",
                {"problem": self.problem.id, "contest": self.contest.id, "source_code": "class Solution {}"},
                format="json",
            )

    def test_extended_student_can_still_submit(self):
        self.assertEqual(self._submit(self.alice).status_code, 201)
        self.assertEqual(self._submit(self.bob).status_code, 400)

    def test_contest_list_status_follows_the_viewers_window(self):
        def ids(user, status):
            self._as(user)
            return [c["id"] for c in self.client.get(f"/api/contests/?status={status}").data["results"]]

        self.assertEqual(ids(self.alice, "active"), [self.contest.id])
        self.assertEqual(ids(self.alice, "past"), [])
        self.assertEqual(ids(self.bob, "active"), [])
        self.assertEqual(ids(self.bob, "past"), [self.contest.id])

    def test_extended_student_keeps_problem_access(self):
        self.assertTrue(user_can_access_unpublished_problem(self.alice, self.problem))
        self.assertFalse(user_can_access_unpublished_problem(self.bob, self.problem))

    def test_contest_detail_reports_the_viewers_own_window(self):
        self._as(self.alice)
        mine = self.client.get(f"/api/contests/{self.contest.id}/").data
        self.assertEqual(mine["my_status"], "active")
        self.assertEqual(mine["status"], "past")
        self._as(self.bob)
        self.assertEqual(self.client.get(f"/api/contests/{self.contest.id}/").data["my_status"], "past")

    def test_scoreboard_counts_solves_within_each_students_window(self):
        self._solve(self.contest, self.alice, 75)  # 15 min past end: inside her 30
        self._solve(self.contest, self.bob, 75)  # outside his window
        board = build_scoreboard(self.contest, viewer=self.admin)
        solved = {row["username"]: row["solved"] for row in board["standings"]}
        self.assertEqual(solved, {"alice": 1, "bob": 0})

    def test_admin_sets_and_removes_extensions(self):
        self._as(self.admin)
        url = f"/api/contests/{self.contest.id}/extensions/"
        resp = self.client.post(url, {"username": "BOB", "extra_minutes": 15}, format="json")
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(resp.data["extra_minutes"], 15)
        self.assertEqual(self._submit(self.bob).status_code, 201)

        self._as(self.admin)
        self.client.post(url, {"username": "alice", "extra_minutes": 0}, format="json")
        self.assertEqual(self._submit(self.alice).status_code, 400)

    def test_extension_validation_and_permissions(self):
        url = f"/api/contests/{self.contest.id}/extensions/"
        self._as(self.admin)
        for body in (
            {"username": "alice", "extra_minutes": -5},
            {"username": "alice", "extra_minutes": "30"},
            {"username": "nobody", "extra_minutes": 30},
            {"extra_minutes": 30},
        ):
            self.assertEqual(self.client.post(url, body, format="json").status_code, 400, body)
        self._as(self.alice)
        self.assertEqual(
            self.client.post(url, {"username": "alice", "extra_minutes": 99}, format="json").status_code,
            403,
        )
