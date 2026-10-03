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


class PracticeAfterEndTests(APITestCase):
    def setUp(self):
        self.alice = User.objects.create_user(username="alice", password="pass12345")
        self.bob = User.objects.create_user(username="bob", password="pass12345")
        # Unpublished: only reachable through a contest.
        self.problem = Problem.objects.create(title="P", slug="p", statement="x", is_published=False)
        ProblemTestCase.objects.create(problem=self.problem, input_data="", expected_output="1")
        now = timezone.now()
        self.past = self._contest(now - timedelta(hours=2), now - timedelta(hours=1), practice_after_end=True)

    def _contest(self, start, end, **fields):
        contest = Contest.objects.create(title="C", start_time=start, end_time=end, **fields)
        ContestProblem.objects.create(contest=contest, problem=self.problem, letter="A")
        return contest

    def _as(self, user):
        token = RefreshToken.for_user(user).access_token
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def _practice(self, user):
        """(detail status, practice submit status) for the user."""
        self._as(user)
        detail = self.client.get(f"/api/problems/{self.problem.slug}/").status_code
        with patch("judge.tasks.judge_submission.delay"):
            submit = self.client.post(
                "/api/submissions/",
                {"problem": self.problem.id, "source_code": "class Solution {}"},
                format="json",
            ).status_code
        return detail, submit

    def test_finished_public_contest_opens_its_problems(self):
        self.assertEqual(self._practice(self.alice), (200, 201))
        # Reached from the contest page; the public list stays published-only.
        self._as(self.alice)
        slugs = [p["slug"] for p in self.client.get("/api/problems/").data["results"]]
        self.assertNotIn("p", slugs)

    def test_closed_unless_the_contest_opts_in(self):
        Contest.objects.filter(pk=self.past.pk).update(practice_after_end=False)
        self.assertEqual(self._practice(self.alice), (404, 400))

    def test_private_contest_opens_only_for_its_participants(self):
        Contest.objects.filter(pk=self.past.pk).update(is_public=False)
        ContestParticipant.objects.create(contest=self.past, user=self.alice)
        self.assertEqual(self._practice(self.alice), (200, 201))
        self.assertEqual(self._practice(self.bob)[1], 400)

    def test_stays_closed_while_reused_in_a_running_contest(self):
        now = timezone.now()
        live = self._contest(now - timedelta(minutes=10), now + timedelta(hours=1))
        ContestParticipant.objects.create(contest=live, user=self.alice)
        # Alice may open it for the live contest, but not submit it as practice.
        self.assertEqual(self._practice(self.alice), (200, 400))
        self.assertEqual(self._practice(self.bob), (404, 400))

    def test_stays_closed_while_a_time_extension_runs(self):
        ContestParticipant.objects.create(contest=self.past, user=self.bob, extra_minutes=90)
        self.assertEqual(self._practice(self.alice)[1], 400)


class PublishedProblemInRunningContestTests(APITestCase):
    """A published problem reused in a contest: while the contest runs for a
    participant, a submission outside it would be a penalty-free test."""

    _contest = PracticeAfterEndTests._contest
    _as = PracticeAfterEndTests._as
    _practice = PracticeAfterEndTests._practice

    def setUp(self):
        self.alice = User.objects.create_user(username="alice", password="pass12345")
        self.bob = User.objects.create_user(username="bob", password="pass12345")
        self.problem = Problem.objects.create(title="P", slug="p", statement="x", is_published=True)
        ProblemTestCase.objects.create(problem=self.problem, input_data="", expected_output="1")
        now = timezone.now()
        self.live = self._contest(now - timedelta(minutes=30), now + timedelta(minutes=30))
        ContestParticipant.objects.create(contest=self.live, user=self.alice)

    def test_participant_cannot_submit_outside_the_contest(self):
        self.assertEqual(self._practice(self.alice), (200, 400))

    def test_non_participant_can_still_practice(self):
        self.assertEqual(self._practice(self.bob), (200, 201))

    def test_open_again_after_the_participants_window(self):
        now = timezone.now()
        Contest.objects.filter(pk=self.live.pk).update(end_time=now - timedelta(minutes=1))
        self.assertEqual(self._practice(self.alice), (200, 201))
