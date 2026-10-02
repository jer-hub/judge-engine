from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework.test import APITestCase
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.views_users import MAX_BULK_RESET
from problems.models import Problem
from submissions.models import Submission

User = get_user_model()


class AccountManagementTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        self.admin = User.objects.create_user(
            username="teacher", password="pass12345", role=User.Role.ADMIN
        )
        self.alice = User.objects.create_user(
            username="alice", password="old-pass-1", class_section="BSIT-1A", first_name="Alice"
        )
        self.bob = User.objects.create_user(
            username="bob", password="old-pass-2", class_section="BSIT-1A"
        )
        self.carol = User.objects.create_user(
            username="carol", password="old-pass-3", class_section="BSIT-1B"
        )
        # An admin who happens to share the section is never reset.
        User.objects.create_user(
            username="ta", password="pass12345", role=User.Role.ADMIN, class_section="BSIT-1A"
        )

    def _as(self, user):
        token = RefreshToken.for_user(user).access_token
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def _login(self, username, password):
        self.client.credentials()
        return self.client.post(
            "/api/auth/login/", {"username": username, "password": password}, format="json"
        ).status_code

    def test_delete_refused_when_user_has_submissions(self):
        problem = Problem.objects.create(title="P", slug="p", statement="x", is_published=True)
        Submission.objects.create(user=self.alice, problem=problem, source_code="x")
        self._as(self.admin)
        resp = self.client.delete(f"/api/users/{self.alice.id}/")
        self.assertEqual(resp.status_code, 409)
        self.assertIn("disable", resp.data["detail"])
        self.assertTrue(User.objects.filter(pk=self.alice.pk).exists())
        # Without history, deleting is still allowed.
        self.assertEqual(self.client.delete(f"/api/users/{self.carol.id}/").status_code, 204)

    def test_bulk_reset_by_section(self):
        session = RefreshToken.for_user(self.alice)  # an existing login
        self._as(self.admin)
        resp = self.client.post(
            "/api/users/bulk-reset-password/", {"section": "bsit-1a"}, format="json"
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual([r["username"] for r in resp.data["results"]], ["alice", "bob"])
        new_password = resp.data["results"][0]["password"]
        self.assertEqual(len(new_password), 10)
        self.assertEqual(self._login("alice", new_password), 200)
        self.assertEqual(self._login("alice", "old-pass-1"), 401)
        self.assertEqual(self._login("carol", "old-pass-3"), 200)  # other section untouched
        self.assertTrue(BlacklistedToken.objects.filter(token__jti=session["jti"]).exists())

    def test_bulk_reset_by_usernames_and_validation(self):
        self._as(self.admin)
        url = "/api/users/bulk-reset-password/"
        resp = self.client.post(url, {"usernames": ["carol", "ta"]}, format="json")
        self.assertEqual([r["username"] for r in resp.data["results"]], ["carol"])
        self.assertEqual(self.client.post(url, {}, format="json").status_code, 400)
        self.assertEqual(self.client.post(url, {"section": "nope"}, format="json").status_code, 400)

    def test_bulk_reset_is_capped(self):
        User.objects.bulk_create(
            User(username=f"s{i}", class_section="BIG") for i in range(MAX_BULK_RESET + 1)
        )
        self._as(self.admin)
        resp = self.client.post("/api/users/bulk-reset-password/", {"section": "BIG"}, format="json")
        self.assertEqual(resp.status_code, 400)

    def test_students_cannot_bulk_reset(self):
        self._as(self.alice)
        resp = self.client.post("/api/users/bulk-reset-password/", {"section": "BSIT-1A"}, format="json")
        self.assertEqual(resp.status_code, 403)
