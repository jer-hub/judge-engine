from datetime import timedelta

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from contests.models import Contest, ContestIntegrityEvent, ContestParticipant, ContestProblem
from problems.models import Problem
from submissions.models import Submission

User = get_user_model()


class ContestIntegrityApiTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="teacher",
            password="pass12345",
            role=User.Role.ADMIN,
            is_staff=True,
        )
        self.alice = User.objects.create_user(
            username="alice", password="pass12345", role=User.Role.STUDENT
        )
        self.bob = User.objects.create_user(
            username="bob", password="pass12345", role=User.Role.STUDENT
        )
        self.problem = Problem.objects.create(
            title="A Plus B",
            slug="a-plus-b-integrity",
            statement="sum",
            is_published=True,
            created_by=self.admin,
        )
        now = timezone.now()
        self.contest = Contest.objects.create(
            title="Integrity Cup",
            start_time=now - timedelta(hours=1),
            end_time=now + timedelta(hours=2),
            is_public=True,
            integrity_monitoring=True,
            created_by=self.admin,
        )
        ContestProblem.objects.create(
            contest=self.contest, problem=self.problem, letter="A", display_order=0
        )
        ContestParticipant.objects.create(contest=self.contest, user=self.alice)
        ContestParticipant.objects.create(contest=self.contest, user=self.bob)

    def _auth(self, user):
        token = RefreshToken.for_user(user).access_token
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def _events_url(self):
        return reverse("contest-integrity-events", kwargs={"pk": self.contest.pk})

    def _summary_url(self):
        return reverse("contest-integrity", kwargs={"pk": self.contest.pk})

    def test_post_events_persists_and_rejects_when_not_registered(self):
        self._auth(self.alice)
        resp = self.client.post(
            self._events_url(),
            {
                "events": [
                    {"type": "window_blur", "count": 2},
                    {"type": "editor_paste", "count": 1, "meta": {"chars": 40, "text": "SECRET"}},
                ]
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data["created"], 2)
        paste = ContestIntegrityEvent.objects.get(
            user=self.alice, event_type=ContestIntegrityEvent.EventType.EDITOR_PASTE
        )
        self.assertEqual(paste.meta, {"chars": 40})
        self.assertNotIn("text", paste.meta)

        outsider = User.objects.create_user(
            username="carol", password="pass12345", role=User.Role.STUDENT
        )
        self._auth(outsider)
        denied = self.client.post(
            self._events_url(),
            {"events": [{"type": "window_blur"}]},
            format="json",
        )
        self.assertEqual(denied.status_code, status.HTTP_403_FORBIDDEN)

    def test_post_rejected_when_monitoring_off_or_outside_window(self):
        self.contest.integrity_monitoring = False
        self.contest.save(update_fields=["integrity_monitoring"])
        self._auth(self.alice)
        off = self.client.post(
            self._events_url(),
            {"events": [{"type": "visibility_hidden"}]},
            format="json",
        )
        self.assertEqual(off.status_code, status.HTTP_403_FORBIDDEN)

        self.contest.integrity_monitoring = True
        self.contest.start_time = timezone.now() + timedelta(hours=1)
        self.contest.end_time = timezone.now() + timedelta(hours=3)
        self.contest.save()
        upcoming = self.client.post(
            self._events_url(),
            {"events": [{"type": "window_blur"}]},
            format="json",
        )
        self.assertEqual(upcoming.status_code, status.HTTP_403_FORBIDDEN)

    def test_student_cannot_get_integrity_summary(self):
        self._auth(self.alice)
        resp = self.client.get(self._summary_url())
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_summary_shared_ip_heuristic(self):
        Submission.objects.create(
            user=self.alice,
            problem=self.problem,
            contest=self.contest,
            source_code="class Solution {}",
            status=Submission.Status.ACCEPTED,
            client_ip="198.51.100.10",
            user_agent="A",
        )
        Submission.objects.create(
            user=self.bob,
            problem=self.problem,
            contest=self.contest,
            source_code="class Solution {}",
            status=Submission.Status.WRONG_ANSWER,
            client_ip="198.51.100.10",
            user_agent="B",
        )
        ContestIntegrityEvent.objects.create(
            contest=self.contest,
            user=self.alice,
            event_type=ContestIntegrityEvent.EventType.WINDOW_BLUR,
            count=3,
        )
        self._auth(self.admin)
        resp = self.client.get(self._summary_url())
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        by_name = {s["username"]: s for s in resp.data["students"]}
        self.assertEqual(by_name["alice"]["window_blur"], 3)
        self.assertEqual(by_name["alice"]["submit_ips"], ["198.51.100.10"])
        self.assertEqual(by_name["alice"]["shared_ip_with"], ["bob"])
        self.assertEqual(by_name["bob"]["shared_ip_with"], ["alice"])

    def test_unknown_event_type_rejected(self):
        self._auth(self.alice)
        resp = self.client.post(
            self._events_url(),
            {"events": [{"type": "webcam_frame"}]},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def _unlock_url(self):
        return reverse("contest-integrity-unlock", kwargs={"pk": self.contest.pk})

    def test_monitor_mode_never_sets_soft_block(self):
        self.contest.integrity_strict = False
        self.contest.save(update_fields=["integrity_strict"])
        self._auth(self.alice)
        resp = self.client.post(
            self._events_url(),
            {"events": [{"type": "fullscreen_exit"}, {"type": "visibility_hidden", "count": 5}]},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertFalse(resp.data["integrity_blocked"])
        p = ContestParticipant.objects.get(contest=self.contest, user=self.alice)
        self.assertFalse(p.integrity_blocked)

    def test_strict_fullscreen_exit_blocks_until_teacher_unlocks(self):
        from unittest.mock import patch

        self.contest.integrity_strict = True
        self.contest.save(update_fields=["integrity_strict"])
        self._auth(self.alice)
        blocked = self.client.post(
            self._events_url(),
            {"events": [{"type": "fullscreen_exit"}]},
            format="json",
        )
        self.assertEqual(blocked.status_code, status.HTTP_201_CREATED)
        self.assertTrue(blocked.data["integrity_blocked"])

        with patch("judge.tasks.judge_submission.delay"):
            submit = self.client.post(
                reverse("submission-list"),
                {
                    "problem": self.problem.id,
                    "contest": self.contest.id,
                    "source_code": "class Solution {}",
                    "language": "java",
                },
                format="json",
            )
        self.assertEqual(submit.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("teacher", str(submit.data).lower())

        # Students cannot unlock themselves.
        denied = self.client.post(
            self._unlock_url(), {"username": "alice"}, format="json"
        )
        self.assertEqual(denied.status_code, status.HTTP_403_FORBIDDEN)

        self._auth(self.admin)
        unlock = self.client.post(
            self._unlock_url(), {"username": "alice"}, format="json"
        )
        self.assertEqual(unlock.status_code, status.HTTP_200_OK)
        self.assertFalse(unlock.data["integrity_blocked"])
        self.assertEqual(unlock.data["integrity_ack_count"], 1)
        ack = ContestIntegrityEvent.objects.filter(
            contest=self.contest,
            user=self.alice,
            event_type=ContestIntegrityEvent.EventType.SOFT_BLOCK_ACK,
        ).latest("created_at")
        self.assertEqual(ack.meta.get("unlocked_by"), self.admin.username)

        self._auth(self.alice)
        with patch("judge.tasks.judge_submission.delay"):
            ok = self.client.post(
                reverse("submission-list"),
                {
                    "problem": self.problem.id,
                    "contest": self.contest.id,
                    "source_code": "class Solution {}",
                    "language": "java",
                },
                format="json",
            )
        self.assertEqual(ok.status_code, status.HTTP_201_CREATED)

    def test_strict_paste_threshold_blocks(self):
        self.contest.integrity_strict = True
        self.contest.save(update_fields=["integrity_strict"])
        self._auth(self.alice)
        resp = self.client.post(
            self._events_url(),
            {"events": [{"type": "editor_paste", "count": 3}]},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertTrue(resp.data["integrity_blocked"])

    def test_strict_focus_threshold_blocks(self):
        self.contest.integrity_strict = True
        self.contest.save(update_fields=["integrity_strict"])
        self._auth(self.alice)
        # window_blur alone is not immediate — need cumulative >= 5
        resp = self.client.post(
            self._events_url(),
            {"events": [{"type": "window_blur", "count": 5}]},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertTrue(resp.data["integrity_blocked"])

    def test_unlock_rejected_when_not_strict(self):
        self.contest.integrity_strict = False
        self.contest.save(update_fields=["integrity_strict"])
        self._auth(self.admin)
        resp = self.client.post(
            self._unlock_url(), {"username": "alice"}, format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_student_cannot_post_soft_block_ack_event(self):
        self.contest.integrity_strict = True
        self.contest.save(update_fields=["integrity_strict"])
        self._auth(self.alice)
        resp = self.client.post(
            self._events_url(),
            {"events": [{"type": "soft_block_ack"}]},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("integrity-unlock", str(resp.data).lower())

    def test_unlock_noop_when_already_unblocked(self):
        """Unlocking a non-blocked student must not wipe counters or bump ack_count."""
        self.contest.integrity_strict = True
        self.contest.save(update_fields=["integrity_strict"])
        p = ContestParticipant.objects.get(contest=self.contest, user=self.alice)
        p.integrity_blocked = False
        p.integrity_focus_since_ack = 2
        p.integrity_paste_since_ack = 1
        p.integrity_ack_count = 0
        p.save()

        self._auth(self.admin)
        resp = self.client.post(
            self._unlock_url(), {"username": "alice"}, format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.data.get("already_unblocked"))
        self.assertFalse(resp.data["integrity_blocked"])
        self.assertEqual(resp.data["integrity_ack_count"], 0)

        p.refresh_from_db()
        self.assertEqual(p.integrity_focus_since_ack, 2)
        self.assertEqual(p.integrity_paste_since_ack, 1)
        self.assertEqual(p.integrity_ack_count, 0)
        self.assertEqual(
            ContestIntegrityEvent.objects.filter(
                contest=self.contest,
                user=self.alice,
                event_type=ContestIntegrityEvent.EventType.SOFT_BLOCK_ACK,
            ).count(),
            0,
        )
