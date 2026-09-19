from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from contests.models import Contest, ContestParticipant, ContestProblem
from contests.scoreboard import build_scoreboard
from problems.models import Problem
from submissions.models import Submission

User = get_user_model()


class ScoreboardTests(TestCase):
    def setUp(self):
        self.u1 = User.objects.create_user(username="alice", password="x")
        self.u2 = User.objects.create_user(username="bob", password="x")
        self.problem = Problem.objects.create(
            title="P",
            slug="p",
            statement="x",
            is_published=True,
        )
        now = timezone.now()
        self.contest = Contest.objects.create(
            title="Week 1",
            start_time=now - timedelta(hours=1),
            end_time=now + timedelta(hours=1),
        )
        ContestProblem.objects.create(
            contest=self.contest,
            problem=self.problem,
            letter="A",
        )
        ContestParticipant.objects.create(contest=self.contest, user=self.u1)
        ContestParticipant.objects.create(contest=self.contest, user=self.u2)

    def test_icpc_ranking_prefers_more_solves_then_lower_penalty(self):
        Submission.objects.create(
            user=self.u1,
            problem=self.problem,
            contest=self.contest,
            source_code="x",
            status=Submission.Status.WRONG_ANSWER,
            submitted_at=self.contest.start_time + timedelta(minutes=5),
        )
        # Force submitted_at (auto_now_add); update after create
        s_wrong = Submission.objects.filter(user=self.u1).first()
        Submission.objects.filter(pk=s_wrong.pk).update(
            submitted_at=self.contest.start_time + timedelta(minutes=5)
        )
        s_ac = Submission.objects.create(
            user=self.u1,
            problem=self.problem,
            contest=self.contest,
            source_code="x",
            status=Submission.Status.ACCEPTED,
        )
        Submission.objects.filter(pk=s_ac.pk).update(
            submitted_at=self.contest.start_time + timedelta(minutes=10)
        )
        s_bob = Submission.objects.create(
            user=self.u2,
            problem=self.problem,
            contest=self.contest,
            source_code="x",
            status=Submission.Status.ACCEPTED,
        )
        Submission.objects.filter(pk=s_bob.pk).update(
            submitted_at=self.contest.start_time + timedelta(minutes=30)
        )

        board = build_scoreboard(self.contest, viewer=None)
        standings = board["standings"]
        self.assertEqual(standings[0]["username"], "alice")
        self.assertEqual(standings[0]["solved"], 1)
        # 10 min + 20 penalty for one wrong
        self.assertEqual(standings[0]["penalty"], 30)
        self.assertEqual(standings[1]["username"], "bob")
        self.assertEqual(standings[1]["penalty"], 30)
