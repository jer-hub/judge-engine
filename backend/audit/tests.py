import secrets
from unittest.mock import patch

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from audit.models import AuditEvent
from problems.models import Problem
from submissions.models import Submission

User = get_user_model()


class AuditTrailTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="teacher", password="pass12345", role=User.Role.ADMIN
        )
        self.student = User.objects.create_user(username="alice", password="pass12345")
        self.problem = Problem.objects.create(title="P", slug="p", statement="x", is_published=True)

    def _as(self, user):
        token = RefreshToken.for_user(user).access_token
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def test_admin_writes_are_recorded_without_values(self):
        new_password = secrets.token_urlsafe(12)
        self._as(self.admin)
        self.client.post(
            f"/api/users/{self.student.id}/reset-password/",
            {"password": new_password},
            format="json",
        )
        self.client.patch(f"/api/problems/{self.problem.slug}/", {"is_published": False}, format="json")
        self.client.delete(f"/api/problems/{self.problem.slug}/")

        events = list(AuditEvent.objects.order_by("id").values("action", "target", "fields", "actor_username"))
        self.assertEqual(
            [e["action"] for e in events],
            ["user.reset_password", "problem.partial_update", "problem.destroy"],
        )
        self.assertEqual(events[0]["fields"], ["password"])
        self.assertIn("P", events[2]["target"])  # label captured before deletion
        self.assertEqual({e["actor_username"] for e in events}, {"teacher"})
        # The new password value is stored nowhere in the trail.
        self.assertNotIn(new_password, str(list(AuditEvent.objects.values())))

    def test_reads_failures_and_student_writes_are_not_recorded(self):
        self._as(self.admin)
        self.client.get("/api/problems/")
        self.client.patch("/api/problems/nope/", {"title": "x"}, format="json")  # 404
        self._as(self.student)
        with patch("judge.tasks.judge_submission.delay"):
            self.client.post(
                "/api/submissions/",
                {"problem": self.problem.id, "source_code": "class Solution {}"},
                format="json",
            )
        self.assertFalse(AuditEvent.objects.exists())

    def test_audit_list_is_admin_only_and_filterable(self):
        AuditEvent.objects.create(actor_username="teacher", action="user.destroy", status_code=204)
        AuditEvent.objects.create(actor_username="ta", action="contest.reveal", status_code=200)
        self._as(self.admin)
        resp = self.client.get("/api/audit/?action=contest.")
        self.assertEqual([e["action"] for e in resp.data["results"]], ["contest.reveal"])
        resp = self.client.get("/api/audit/?actor=TEACHER")
        self.assertEqual([e["action"] for e in resp.data["results"]], ["user.destroy"])
        self._as(self.student)
        self.assertEqual(self.client.get("/api/audit/").status_code, 403)


class JudgeHealthTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="teacher", password="pass12345", role=User.Role.ADMIN
        )
        problem = Problem.objects.create(title="P", slug="p", statement="x", is_published=True)
        for status in (Submission.Status.PENDING, Submission.Status.PENDING, Submission.Status.SYSTEM_ERROR):
            Submission.objects.create(user=self.admin, problem=problem, source_code="x", status=status)

    def test_reports_workers_queues_and_states(self):
        token = RefreshToken.for_user(self.admin).access_token
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        with patch("judge.health._worker_pings", return_value=[{"name": "judge@w1", "ok": True}]), \
                patch("judge.health._queue_lengths", return_value={"judge": 3, "preview": 0, "celery": 0}):
            data = self.client.get("/api/judge/health/").data
        self.assertTrue(data["judge_worker_up"])
        self.assertFalse(data["preview_worker_up"])
        self.assertEqual(data["queues"]["judge"], 3)
        self.assertEqual(data["submissions"]["pending"], 2)
        self.assertEqual(data["submissions"]["system_error"], 1)
        self.assertIsNotNone(data["submissions"]["oldest_pending_seconds"])
