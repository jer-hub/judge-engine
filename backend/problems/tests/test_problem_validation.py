from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from problems.constants import MIN_MEMORY_LIMIT_MB, MIN_TIME_LIMIT_MS
from problems.models import Problem
from problems.models import TestCase as ProblemTestCase
from problems.tags import normalize_tags

User = get_user_model()


class TagNormalizeTests(TestCase):
    def test_normalize_lowercases_dedupes(self):
        self.assertEqual(normalize_tags("Array, DP ,array"), "array,dp")
        self.assertEqual(normalize_tags("  ,  "), "")
        self.assertEqual(normalize_tags(None), "")

    def test_save_normalizes_tags(self):
        p = Problem.objects.create(
            title="Tag Norm",
            statement="s",
            tags="Array, array, DP",
        )
        self.assertEqual(p.tags, "array,dp")


class ProblemValidationApiTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin_val",
            password="pass12345",
            role=User.Role.ADMIN,
            is_staff=True,
        )
        self._auth(self.admin)

    def _auth(self, user):
        token = RefreshToken.for_user(user).access_token
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def test_invalid_limits_rejected(self):
        resp = self.client.post(
            reverse("problem-list"),
            {
                "title": "Bad Limits",
                "statement": "s",
                "time_limit_ms": 0,
                "memory_limit_mb": 1,
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("time_limit_ms", resp.data)
        self.assertIn("memory_limit_mb", resp.data)

    def test_boundary_limits_accepted(self):
        resp = self.client.post(
            reverse("problem-list"),
            {
                "title": "Ok Limits",
                "statement": "s",
                "time_limit_ms": MIN_TIME_LIMIT_MS,
                "memory_limit_mb": MIN_MEMORY_LIMIT_MB,
                "test_cases": [
                    {
                        "order": 0,
                        "input_data": "1\n",
                        "expected_output": "1\n",
                        "is_sample": True,
                        "points": 1,
                    }
                ],
                "is_published": True,
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

    def test_slug_immutable_on_patch(self):
        problem = Problem.objects.create(
            title="Slug Lock",
            slug="slug-lock",
            statement="s",
            created_by=self.admin,
        )
        ProblemTestCase.objects.create(
            problem=problem,
            input_data="1\n",
            expected_output="1\n",
            is_sample=True,
        )
        resp = self.client.patch(
            reverse("problem-detail", kwargs={"slug": "slug-lock"}),
            {"slug": "renamed", "title": "Slug Lock Updated"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        problem.refresh_from_db()
        self.assertEqual(problem.slug, "slug-lock")
        self.assertEqual(problem.title, "Slug Lock Updated")

    def test_publish_without_tests_rejected(self):
        problem = Problem.objects.create(
            title="No Cases",
            slug="no-cases",
            statement="s",
            created_by=self.admin,
        )
        resp = self.client.patch(
            reverse("problem-detail", kwargs={"slug": problem.slug}),
            {"is_published": True},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("is_published", resp.data)

    def test_exact_tag_filter_not_substring(self):
        Problem.objects.create(
            title="Arrays Only",
            slug="arrays-only",
            statement="s",
            is_published=True,
            tags="arrays",
        )
        Problem.objects.create(
            title="Array Exact",
            slug="array-exact",
            statement="s",
            is_published=True,
            tags="array",
        )
        resp = self.client.get(reverse("problem-list"), {"tag": "array"})
        slugs = {r["slug"] for r in resp.data["results"]}
        self.assertIn("array-exact", slugs)
        self.assertNotIn("arrays-only", slugs)

    def test_multi_tag_and_filter(self):
        Problem.objects.create(
            title="Both Tags",
            slug="both-tags",
            statement="s",
            is_published=True,
            tags="math,dp",
        )
        Problem.objects.create(
            title="Math Only",
            slug="math-only-2",
            statement="s",
            is_published=True,
            tags="math",
        )
        resp = self.client.get(reverse("problem-list"), {"tag": "math,dp"})
        slugs = {r["slug"] for r in resp.data["results"]}
        self.assertIn("both-tags", slugs)
        self.assertNotIn("math-only-2", slugs)
