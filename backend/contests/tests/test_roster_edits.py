from datetime import timedelta

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from contests.models import Contest, ContestParticipant

User = get_user_model()


class RosterEditTests(APITestCase):
    """Saving the contest editor must not drop students who registered
    themselves after the editor was loaded."""

    def setUp(self):
        admin = User.objects.create_user(
            username="r_admin", password="pass12345", role=User.Role.ADMIN
        )
        self.alice = User.objects.create_user(username="alice", password="pass12345")
        self.bob = User.objects.create_user(username="bob", password="pass12345")
        self.carol = User.objects.create_user(username="carol", password="pass12345")
        now = timezone.now()
        self.contest = Contest.objects.create(
            title="Roster Cup",
            start_time=now - timedelta(hours=1),
            end_time=now + timedelta(hours=1),
            is_public=True,
        )
        ContestParticipant.objects.create(contest=self.contest, user=self.alice, extra_minutes=20)
        token = RefreshToken.for_user(admin).access_token
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def _patch(self, body):
        return self.client.patch(
            reverse("contest-detail", kwargs={"pk": self.contest.id}), body, format="json"
        )

    def _roster(self):
        return set(
            ContestParticipant.objects.filter(contest=self.contest)
            .values_list("user__username", flat=True)
        )

    def test_unrelated_edit_keeps_late_self_registration(self):
        # The editor loaded [alice]; bob registers; the admin fixes a typo.
        ContestParticipant.objects.create(contest=self.contest, user=self.bob)
        resp = self._patch({"description": "fixed typo"})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(self._roster(), {"alice", "bob"})

    def test_add_and_remove_touch_only_the_named_users(self):
        ContestParticipant.objects.create(contest=self.contest, user=self.bob)
        resp = self._patch({"participants_add": ["carol"], "participants_remove": ["bob"]})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(self._roster(), {"alice", "carol"})
        # alice was untouched, so her time extension survives.
        self.assertEqual(
            ContestParticipant.objects.get(contest=self.contest, user=self.alice).extra_minutes, 20
        )

    def test_adding_an_unknown_user_is_rejected(self):
        resp = self._patch({"participants_add": ["nobody"]})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("participants_add", resp.data)
        self.assertEqual(self._roster(), {"alice"})

    def test_full_roster_still_replaces(self):
        resp = self._patch({"participant_usernames": ["bob"]})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(self._roster(), {"bob"})
