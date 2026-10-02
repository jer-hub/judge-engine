import csv
import io
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from contests.models import Contest, ContestParticipant, ContestProblem
from problems.models import Problem
from submissions.models import Submission

User = get_user_model()


class StandingsExportTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="teacher", password="pass12345", role=User.Role.ADMIN
        )
        self.alice = User.objects.create_user(
            username="alice", password="x", first_name="Alice", last_name="Peña",
            school_id="S-1", class_section="BSIT-1A",
        )
        self.bob = User.objects.create_user(
            username="bob", password="x", first_name="=HYPERLINK(\"x\")",
            class_section="BSIT-1B",
        )
        self.problem = Problem.objects.create(title="P", slug="p", statement="x", is_published=True)
        now = timezone.now()
        self.contest = Contest.objects.create(
            title="Week 1 Quiz", start_time=now - timedelta(hours=2), end_time=now - timedelta(hours=1),
        )
        ContestProblem.objects.create(contest=self.contest, problem=self.problem, letter="A")
        for user in (self.alice, self.bob):
            ContestParticipant.objects.create(contest=self.contest, user=user)
        for status, minutes in ((Submission.Status.WRONG_ANSWER, 5), (Submission.Status.ACCEPTED, 12)):
            sub = Submission.objects.create(
                user=self.alice, problem=self.problem, contest=self.contest,
                source_code="x", status=status,
            )
            Submission.objects.filter(pk=sub.pk).update(
                submitted_at=self.contest.start_time + timedelta(minutes=minutes)
            )

    def _get(self, user, query=""):
        token = RefreshToken.for_user(user).access_token
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        return self.client.get(f"/api/contests/{self.contest.id}/standings-export/{query}")

    def _rows(self, resp):
        text = resp.content.decode("utf-8")
        self.assertTrue(text.startswith("﻿"))
        return list(csv.reader(io.StringIO(text.lstrip("﻿"))))

    def test_admin_downloads_standings(self):
        resp = self._get(self.admin)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp["Content-Type"].startswith("text/csv"))
        self.assertIn('filename="week-1-quiz-standings.csv"', resp["Content-Disposition"])
        header, first, second = self._rows(resp)
        self.assertEqual(
            header,
            ["Rank", "Username", "First name", "Last name", "School ID", "Section",
             "Solved", "Penalty", "A solved at (min)", "A attempts"],
        )
        # 12 min + 20 for the wrong attempt; attempts include the accepted one.
        self.assertEqual(first, ["1", "alice", "Alice", "Peña", "S-1", "BSIT-1A", "1", "32", "12", "2"])
        self.assertEqual(second[1], "bob")
        self.assertEqual(second[8:], ["", "0"])

    def test_formula_like_cells_are_escaped(self):
        rows = self._rows(self._get(self.admin))
        bob = next(r for r in rows if r[1] == "bob")
        self.assertEqual(bob[2], "'=HYPERLINK(\"x\")")

    def test_section_filter(self):
        resp = self._get(self.admin, "?section=bsit-1b")
        self.assertIn("bsit-1b", resp["Content-Disposition"])
        rows = self._rows(resp)
        self.assertEqual([r[1] for r in rows[1:]], ["bob"])

    def test_students_cannot_export(self):
        self.assertEqual(self._get(self.alice).status_code, 403)
