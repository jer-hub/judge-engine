from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from problems.models import Problem, TestCase

User = get_user_model()


class ProblemApiCharacterizationTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin_prob",
            password="pass12345",
            role=User.Role.ADMIN,
            is_staff=True,
        )
        self.student = User.objects.create_user(
            username="student_prob",
            password="pass12345",
            role=User.Role.STUDENT,
        )
        self.published = Problem.objects.create(
            title="Published Sum",
            slug="published-sum",
            statement="Add two numbers.",
            is_published=True,
            difficulty="easy",
            tags="math,warmup",
            created_by=self.admin,
        )
        TestCase.objects.create(
            problem=self.published,
            input_data="1 2\n",
            expected_output="3\n",
            is_sample=True,
            order=0,
        )
        TestCase.objects.create(
            problem=self.published,
            input_data="4 5\n",
            expected_output="9\n",
            is_sample=False,
            order=1,
        )
        self.draft = Problem.objects.create(
            title="Draft Only",
            slug="draft-only",
            statement="Hidden draft.",
            is_published=False,
            difficulty="hard",
            tags="graph",
            created_by=self.admin,
        )

    def _auth(self, user):
        token = RefreshToken.for_user(user).access_token
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def test_student_lists_only_published(self):
        self._auth(self.student)
        resp = self.client.get(reverse("problem-list"))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        slugs = {row["slug"] for row in resp.data["results"]}
        self.assertIn("published-sum", slugs)
        self.assertNotIn("draft-only", slugs)

    def test_admin_lists_unpublished(self):
        self._auth(self.admin)
        resp = self.client.get(reverse("problem-list"))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        slugs = {row["slug"] for row in resp.data["results"]}
        self.assertIn("draft-only", slugs)
        self.assertIn("test_case_count", resp.data["results"][0])

    def test_detail_exposes_only_samples(self):
        self._auth(self.student)
        resp = self.client.get(
            reverse("problem-detail", kwargs={"slug": self.published.slug})
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data["sample_tests"]), 1)
        self.assertEqual(resp.data["sample_tests"][0]["input_data"], "1 2\n")

    def test_student_cannot_see_draft_detail(self):
        self._auth(self.student)
        resp = self.client.get(
            reverse("problem-detail", kwargs={"slug": self.draft.slug})
        )
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_student_write_forbidden(self):
        self._auth(self.student)
        resp = self.client.post(
            reverse("problem-list"),
            {
                "title": "Nope",
                "statement": "x",
                "difficulty": "easy",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_difficulty_and_tag_filters(self):
        self._auth(self.student)
        resp = self.client.get(reverse("problem-list"), {"difficulty": "easy"})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(all(r["difficulty"] == "easy" for r in resp.data["results"]))

        resp = self.client.get(reverse("problem-list"), {"tag": "math"})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(resp.data["count"], 1)

    def test_slug_autogenerates_and_collides(self):
        p1 = Problem.objects.create(title="Hello World", statement="s")
        p2 = Problem.objects.create(title="Hello World", statement="s")
        self.assertEqual(p1.slug, "hello-world")
        self.assertEqual(p2.slug, "hello-world-2")

    def test_tag_list_property(self):
        self.assertEqual(self.published.tag_list, ["math", "warmup"])
