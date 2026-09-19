from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from problems.models import Problem, TestCase

User = get_user_model()


class ProblemSearchPaginationTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin_search",
            password="pass12345",
            role=User.Role.ADMIN,
            is_staff=True,
        )
        self.student = User.objects.create_user(
            username="student_search",
            password="pass12345",
            role=User.Role.STUDENT,
        )
        for i in range(25):
            Problem.objects.create(
                title=f"Alpha Problem {i:02d}",
                slug=f"alpha-{i:02d}",
                statement="s",
                is_published=True,
                tags="loops" if i % 2 == 0 else "math",
                created_by=self.admin,
            )
        Problem.objects.create(
            title="Hidden Beta",
            slug="hidden-beta",
            statement="s",
            is_published=False,
            tags="graph",
            created_by=self.admin,
        )

    def _auth(self, user):
        token = RefreshToken.for_user(user).access_token
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def test_search_matches_title_slug_tags(self):
        self._auth(self.student)
        resp = self.client.get(reverse("problem-list"), {"search": "Alpha Problem 01"})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["count"], 1)

        resp = self.client.get(reverse("problem-list"), {"search": "alpha-02"})
        self.assertEqual(resp.data["count"], 1)

        resp = self.client.get(reverse("problem-list"), {"search": "loops"})
        self.assertGreaterEqual(resp.data["count"], 1)

    def test_search_empty_results(self):
        self._auth(self.student)
        resp = self.client.get(reverse("problem-list"), {"search": "zzzz-no-match"})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["count"], 0)
        self.assertEqual(resp.data["results"], [])

    def test_page_size_honored_and_clamped(self):
        self._auth(self.student)
        resp = self.client.get(reverse("problem-list"), {"page_size": 1})
        self.assertEqual(len(resp.data["results"]), 1)
        self.assertIsNotNone(resp.data["next"])

        resp = self.client.get(reverse("problem-list"), {"page_size": 9999})
        self.assertLessEqual(len(resp.data["results"]), 100)

    def test_is_published_filter_admin_only(self):
        self._auth(self.admin)
        resp = self.client.get(reverse("problem-list"), {"is_published": "false"})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(all(not r["is_published"] for r in resp.data["results"]))

        self._auth(self.student)
        resp = self.client.get(reverse("problem-list"), {"is_published": "false"})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(all(r["is_published"] for r in resp.data["results"]))

    def test_combined_filters_and_page(self):
        self._auth(self.student)
        resp = self.client.get(
            reverse("problem-list"),
            {"search": "Alpha", "difficulty": "easy", "page": 2, "page_size": 10},
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data["results"]), 10)
        self.assertIsNotNone(resp.data["previous"])
