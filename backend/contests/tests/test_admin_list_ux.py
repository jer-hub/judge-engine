"""Admin contest list UX: search, summary badges, archive, bulk, delete rules."""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from contests.models import Clarification, Contest, ContestParticipant, ContestProblem
from problems.models import Problem
from problems.models import TestCase as ProblemTestCase
from submissions.models import Submission

User = get_user_model()


class ContestAdminListUxTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="ux_admin",
            password="pass12345",
            role=User.Role.ADMIN,
            is_staff=True,
        )
        self.alice = User.objects.create_user(
            username="ux_alice", password="pass12345", role=User.Role.STUDENT
        )
        now = timezone.now()
        self.contest = Contest.objects.create(
            title="Alpha Cup UX",
            start_time=now - timedelta(hours=1),
            end_time=now + timedelta(hours=2),
            is_public=True,
            integrity_monitoring=True,
            integrity_strict=True,
            hold_results_until_revealed=True,
            created_by=self.admin,
        )
        self.other = Contest.objects.create(
            title="Beta Practice",
            start_time=now + timedelta(days=1),
            end_time=now + timedelta(days=1, hours=2),
            is_public=False,
            created_by=self.admin,
        )
        ContestParticipant.objects.create(
            contest=self.contest, user=self.alice, integrity_blocked=True
        )
        Clarification.objects.create(
            contest=self.contest,
            author=self.alice,
            question="What about sample 2?",
        )

    def _auth(self, user):
        token = RefreshToken.for_user(user).access_token
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def test_search_filters_by_title(self):
        self._auth(self.admin)
        resp = self.client.get(reverse("contest-list"), {"search": "Alpha"})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        titles = [c["title"] for c in resp.data["results"]]
        self.assertIn("Alpha Cup UX", titles)
        self.assertNotIn("Beta Practice", titles)

    def test_list_summary_fields_for_admin(self):
        self._auth(self.admin)
        resp = self.client.get(reverse("contest-list"), {"search": "Alpha"})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        row = resp.data["results"][0]
        self.assertTrue(row["integrity_monitoring"])
        self.assertTrue(row["integrity_strict"])
        self.assertTrue(row["results_held"])
        self.assertEqual(row["blocked_count"], 1)
        self.assertEqual(row["clarifications_waiting"], 1)
        self.assertFalse(row["is_archived"])

    def test_students_do_not_see_archived(self):
        self.contest.is_archived = True
        self.contest.save(update_fields=["is_archived"])
        ContestParticipant.objects.get_or_create(contest=self.contest, user=self.alice)
        self._auth(self.alice)
        resp = self.client.get(reverse("contest-list"))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        ids = [c["id"] for c in resp.data["results"]]
        self.assertNotIn(self.contest.id, ids)

    def test_admin_archived_filter(self):
        self.contest.is_archived = True
        self.contest.save(update_fields=["is_archived"])
        self._auth(self.admin)
        archived = self.client.get(reverse("contest-list"), {"status": "archived"})
        self.assertEqual(archived.status_code, status.HTTP_200_OK)
        ids = [c["id"] for c in archived.data["results"]]
        self.assertIn(self.contest.id, ids)
        self.assertNotIn(self.other.id, ids)

        active = self.client.get(reverse("contest-list"), {"status": "active"})
        active_ids = [c["id"] for c in active.data["results"]]
        self.assertNotIn(self.contest.id, active_ids)

    def test_archive_and_unarchive(self):
        self._auth(self.admin)
        url = reverse("contest-archive", kwargs={"pk": self.contest.pk})
        resp = self.client.post(url, {"archived": True}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.contest.refresh_from_db()
        self.assertTrue(self.contest.is_archived)

        resp = self.client.post(url, {"archived": False}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.contest.refresh_from_db()
        self.assertFalse(self.contest.is_archived)

    def test_student_cannot_archive(self):
        self._auth(self.alice)
        resp = self.client.post(
            reverse("contest-archive", kwargs={"pk": self.contest.pk}),
            {"archived": True},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_bulk_archive_and_visibility(self):
        self._auth(self.admin)
        url = reverse("contest-bulk")
        resp = self.client.post(
            url,
            {"ids": [self.contest.id, self.other.id], "action": "archive"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["updated"], 2)
        self.contest.refresh_from_db()
        self.other.refresh_from_db()
        self.assertTrue(self.contest.is_archived)
        self.assertTrue(self.other.is_archived)

        resp = self.client.post(
            url,
            {"ids": [self.other.id], "action": "set_public"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.other.refresh_from_db()
        self.assertTrue(self.other.is_public)

        resp = self.client.post(
            url,
            {"ids": [self.other.id], "action": "set_invite_only"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.other.refresh_from_db()
        self.assertFalse(self.other.is_public)

    def test_destroy_archived_ok(self):
        self.contest.is_archived = True
        self.contest.save(update_fields=["is_archived"])
        self._auth(self.admin)
        resp = self.client.delete(reverse("contest-detail", kwargs={"pk": self.contest.pk}))
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Contest.objects.filter(pk=self.contest.pk).exists())

    def test_destroy_active_with_submissions_rejected(self):
        problem = Problem.objects.create(
            title="P", slug="ux-p", statement="s", is_published=True, created_by=self.admin
        )
        ProblemTestCase.objects.create(
            problem=problem, input_data="1\n", expected_output="1\n", is_sample=True
        )
        ContestProblem.objects.create(
            contest=self.contest, problem=problem, letter="A", display_order=0
        )
        Submission.objects.create(
            user=self.alice,
            problem=problem,
            contest=self.contest,
            language="java",
            source_code="class Solution {}",
            status=Submission.Status.ACCEPTED,
        )
        self._auth(self.admin)
        resp = self.client.delete(reverse("contest-detail", kwargs={"pk": self.contest.pk}))
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(Contest.objects.filter(pk=self.contest.pk).exists())

    def test_destroy_upcoming_empty_ok(self):
        self._auth(self.admin)
        resp = self.client.delete(reverse("contest-detail", kwargs={"pk": self.other.pk}))
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Contest.objects.filter(pk=self.other.pk).exists())
