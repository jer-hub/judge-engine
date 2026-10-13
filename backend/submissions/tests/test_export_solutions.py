import csv
import io
import zipfile
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from contests.models import Contest, ContestProblem
from problems.models import Problem
from submissions.models import Submission

User = get_user_model()
URL = "/api/submissions/export/"


class ExportSolutionsTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username="teacher", password="pass12345", role=User.Role.ADMIN)
        self.alice = User.objects.create_user(
            username="alice", password="pass12345", first_name="Alice", class_section="BSIT-1A"
        )
        self.bob = User.objects.create_user(
            username="bob", password="pass12345", first_name="=HYPERLINK(1)", class_section="BSIT-1B"
        )
        self.problem = Problem.objects.create(title="A Plus B", slug="a-plus-b", statement="x")
        self.other = Problem.objects.create(title="Other", slug="other", statement="x")
        now = timezone.now()
        self.contest = Contest.objects.create(
            title="Quiz 1", start_time=now - timedelta(hours=1), end_time=now + timedelta(hours=1)
        )
        ContestProblem.objects.create(contest=self.contest, problem=self.problem, letter="A")
        self.code = "public class Solution {\n  // ñ, café\n}\n"
        self.s1 = self._sub(self.alice, Submission.Status.WRONG_ANSWER)
        self.s2 = self._sub(self.alice, Submission.Status.ACCEPTED)
        self.s3 = self._sub(self.bob, Submission.Status.COMPILE_ERROR)
        self.practice = Submission.objects.create(
            user=self.alice, problem=self.other, source_code="x", status=Submission.Status.ACCEPTED
        )

    def _sub(self, user, status):
        return Submission.objects.create(
            user=user, problem=self.problem, contest=self.contest, source_code=self.code, status=status
        )

    def _get(self, user, query):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(user).access_token}")
        return self.client.get(URL, query)

    def _zip(self, resp):
        self.assertEqual(resp.status_code, 200, getattr(resp, "data", None))
        self.assertEqual(resp["Content-Type"], "application/zip")
        return zipfile.ZipFile(io.BytesIO(resp.content))

    def test_contest_export_has_every_solution_and_an_index(self):
        resp = self._get(self.admin, {"contest": self.contest.id})
        self.assertIn('filename="quiz-1-solutions-', resp["Content-Disposition"])
        zf = self._zip(resp)
        java = sorted(n for n in zf.namelist() if n.endswith(".java"))
        self.assertEqual(len(java), 3)  # the practice submission is not in the contest
        self.assertTrue(all(n.split("/")[1] == "A-a-plus-b" for n in java))
        self.assertTrue(any(n.startswith("alice/") and n.endswith(f"_#{self.s2.id}_Accepted.java") for n in java))
        self.assertTrue(any(n.startswith("bob/") and n.endswith(f"_#{self.s3.id}_CompileError.java") for n in java))
        # The code is stored exactly as submitted, accents included.
        self.assertEqual(zf.read(java[0]).decode("utf-8"), self.code)

        rows = list(csv.DictReader(io.StringIO(zf.read("index.csv").decode("utf-8-sig"))))
        self.assertEqual(len(rows), 3)
        bob_row = next(r for r in rows if r["username"] == "bob")
        self.assertEqual(bob_row["first_name"], "'=HYPERLINK(1)")  # no spreadsheet formulas
        self.assertEqual(bob_row["letter"], "A")
        self.assertIn(bob_row["file"], zf.namelist())

    def test_problem_and_section_filters(self):
        zf = self._zip(self._get(self.admin, {"problem": self.other.id}))
        self.assertEqual([n for n in zf.namelist() if n.endswith(".java")][0].split("/")[:2], ["alice", "other"])
        zf = self._zip(self._get(self.admin, {"contest": self.contest.id, "section": "bsit-1b"}))
        java = [n for n in zf.namelist() if n.endswith(".java")]
        self.assertEqual(len(java), 1)
        self.assertTrue(java[0].startswith("bob/"))

    def test_needs_a_scope_and_something_to_export(self):
        self.assertEqual(self._get(self.admin, {}).status_code, 400)
        self.assertEqual(self._get(self.admin, {"contest": 999}).status_code, 400)
        resp = self._get(self.admin, {"contest": self.contest.id, "section": "nobody"})
        self.assertEqual(resp.status_code, 400)
        self.assertIn("No submissions", str(resp.data))

    def test_students_cannot_export(self):
        self.assertEqual(self._get(self.alice, {"contest": self.contest.id}).status_code, 403)
