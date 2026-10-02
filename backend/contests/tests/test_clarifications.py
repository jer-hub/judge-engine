from datetime import timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from contests.clarifications import MAX_QUESTIONS_PER_STUDENT
from contests.models import Clarification, Contest, ContestParticipant, ContestProblem
from problems.models import Problem

User = get_user_model()


class ClarificationTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="teacher", password="pass12345", role=User.Role.ADMIN
        )
        self.alice = User.objects.create_user(username="alice", password="pass12345")
        self.bob = User.objects.create_user(username="bob", password="pass12345")
        self.outsider = User.objects.create_user(username="eve", password="pass12345")
        problem = Problem.objects.create(title="P", slug="p", statement="x", is_published=True)
        now = timezone.now()
        self.contest = Contest.objects.create(
            title="Live", start_time=now - timedelta(minutes=10), end_time=now + timedelta(hours=1)
        )
        ContestProblem.objects.create(contest=self.contest, problem=problem, letter="A")
        for user in (self.alice, self.bob):
            ContestParticipant.objects.create(contest=self.contest, user=user)
        self.url = f"/api/contests/{self.contest.id}/clarifications/"

    def _as(self, user):
        token = RefreshToken.for_user(user).access_token
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def _ask(self, user, question="Is n ever 0?", **extra):
        self._as(user)
        return self.client.post(self.url, {"question": question, **extra}, format="json")

    def _seen(self, user):
        self._as(user)
        return self.client.get(self.url).data

    def test_question_is_private_until_published(self):
        resp = self._ask(self.alice, problem_letter="a")
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertEqual(resp.data["problem_letter"], "A")
        self.assertEqual(len(self._seen(self.alice)), 1)
        self.assertEqual(self._seen(self.bob), [])

        # Admin answers privately: still only alice sees it.
        self._as(self.admin)
        answer_url = f"{self.url}{resp.data['id']}/answer/"
        answered = self.client.post(answer_url, {"answer": "No.", "is_public": False}, format="json")
        self.assertEqual(answered.status_code, 200)
        self.assertEqual(self._seen(self.alice)[0]["answer"], "No.")
        self.assertEqual(self._seen(self.bob), [])

        # Published: everyone sees it, but not who asked.
        self._as(self.admin)
        self.client.post(answer_url, {"answer": "No, n >= 1.", "is_public": True}, format="json")
        bob_view = self._seen(self.bob)
        self.assertEqual([c["answer"] for c in bob_view], ["No, n >= 1."])
        self.assertIsNone(bob_view[0]["author"])
        self.assertFalse(bob_view[0]["mine"])
        self.assertEqual(self._seen(self.admin)[0]["author"], "alice")

    def test_admin_announcement_reaches_everyone(self):
        self._as(self.admin)
        resp = self.client.post(self.url, {"answer": "Sample 2 was fixed."}, format="json")
        self.assertEqual(resp.status_code, 201)
        self.assertTrue(resp.data["is_announcement"])
        for user in (self.alice, self.bob):
            self.assertEqual([c["answer"] for c in self._seen(user)], ["Sample 2 was fixed."])

    def test_who_may_ask(self):
        self.assertEqual(self._ask(self.outsider).status_code, 400)  # not registered
        self.assertEqual(self._ask(self.alice, question="  ").status_code, 400)
        self.assertEqual(self._ask(self.alice, problem_letter="Z").status_code, 400)
        Contest.objects.filter(pk=self.contest.pk).update(end_time=timezone.now() - timedelta(minutes=1))
        self.assertEqual(self._ask(self.alice).status_code, 400)  # contest over

    def test_question_cap(self):
        for i in range(MAX_QUESTIONS_PER_STUDENT):
            Clarification.objects.create(contest=self.contest, author=self.alice, question=f"q{i}")
        self.assertEqual(self._ask(self.alice).status_code, 400)

    def test_only_admins_answer(self):
        item = Clarification.objects.create(contest=self.contest, author=self.alice, question="q")
        self._as(self.bob)
        resp = self.client.post(f"{self.url}{item.id}/answer/", {"answer": "x"}, format="json")
        self.assertEqual(resp.status_code, 403)
