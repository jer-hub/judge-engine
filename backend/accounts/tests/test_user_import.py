import json

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()


class UserImportApiTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="import_admin",
            password="pass12345",
            role=User.Role.ADMIN,
            is_staff=True,
        )
        self.student = User.objects.create_user(
            username="import_student",
            password="pass12345",
            role=User.Role.STUDENT,
        )
        self.url = reverse("user-import")

    def _auth(self, user):
        token = RefreshToken.for_user(user).access_token
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def test_anonymous_rejected(self):
        resp = self.client.post(self.url, {"csv_text": "username,password\na,pass12345\n"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_student_forbidden(self):
        self._auth(self.student)
        resp = self.client.post(
            self.url,
            {"csv_text": "username,password\nalice,pass12345\n"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_creates_student_accounts(self):
        self._auth(self.admin)
        csv_text = (
            "username,password,first_name,school_id,class_section\n"
            "alice,pass12345,Alice,S1,7A\n"
            "bob,pass12345,Bob,S2,7B\n"
            "carol,pass12345,Carol,,\n"
        )
        before = User.objects.count()
        resp = self.client.post(self.url, {"csv_text": csv_text, "dry_run": False}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["created"], 3)
        self.assertEqual(resp.data["skipped"], 0)
        self.assertEqual(resp.data["failed"], 0)
        self.assertEqual(User.objects.count(), before + 3)
        alice = User.objects.get(username="alice")
        self.assertEqual(alice.role, User.Role.STUDENT)
        self.assertFalse(alice.is_staff)
        self.assertTrue(alice.check_password("pass12345"))
        self.assertEqual(alice.class_section, "7A")

    def test_mixed_batch_partial_success(self):
        self._auth(self.admin)
        User.objects.create_user(username="exists", password="oldpass12", role=User.Role.STUDENT)
        csv_text = (
            "username,password\n"
            "newkid,pass12345\n"
            "exists,pass12345\n"
            "short,pass\n"
        )
        resp = self.client.post(self.url, {"csv_text": csv_text}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["created"], 1)
        self.assertEqual(resp.data["skipped"], 1)
        self.assertEqual(resp.data["failed"], 1)
        self.assertTrue(User.objects.filter(username="newkid").exists())
        self.assertTrue(User.objects.get(username="exists").check_password("oldpass12"))
        failed_rows = {e["row"] for e in resp.data["errors"]}
        self.assertIn(4, failed_rows)

    def test_dry_run_does_not_create(self):
        self._auth(self.admin)
        before = User.objects.count()
        csv_text = "username,password\ndryuser,pass12345\n"
        resp = self.client.post(self.url, {"csv_text": csv_text, "dry_run": True}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.data["dry_run"])
        self.assertEqual(resp.data["created"], 1)
        self.assertEqual(User.objects.count(), before)
        self.assertFalse(User.objects.filter(username="dryuser").exists())

    def test_missing_header_is_400(self):
        self._auth(self.admin)
        resp = self.client.post(
            self.url,
            {"csv_text": "username\nalice\n"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_passwords_never_echoed(self):
        self._auth(self.admin)
        secret = "SuperSecret99"
        csv_text = f"username,password\necho_user,{secret}\nbaduser,short\n"
        resp = self.client.post(self.url, {"csv_text": csv_text}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        body = json.dumps(resp.data)
        self.assertNotIn(secret, body)
        self.assertNotIn("short", body)

    def test_common_password_rejected(self):
        self._auth(self.admin)
        csv_text = "username,password\nweakuser,password\n"
        resp = self.client.post(self.url, {"csv_text": csv_text}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["created"], 0)
        self.assertEqual(resp.data["failed"], 1)
        self.assertFalse(User.objects.filter(username="weakuser").exists())
        self.assertTrue(any("password" in e["error"].lower() for e in resp.data["errors"]))
