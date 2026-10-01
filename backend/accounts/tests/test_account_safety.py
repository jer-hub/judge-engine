from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient, APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()

STRONG = "Correct-Horse-Battery-9"


class AccountSafetyTests(APITestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(
            username="teacher", password=STRONG, role=User.Role.ADMIN
        )
        self.root = User.objects.create_superuser(
            username="root", password=STRONG, email="root@example.com"
        )
        self.student = User.objects.create_user(username="stu", password=STRONG)

    def _as(self, user):
        token = RefreshToken.for_user(user).access_token
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    # --- superusers can only be modified by superusers -------------------

    def test_teacher_cannot_reset_superuser_password(self):
        self._as(self.teacher)
        resp = self.client.post(
            f"/api/users/{self.root.id}/reset-password/", {"password": "Taken-Over-Pass-1"}
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
        self.root.refresh_from_db()
        self.assertTrue(self.root.check_password(STRONG))

    def test_teacher_cannot_edit_or_delete_superuser(self):
        self._as(self.teacher)
        patch_resp = self.client.patch(f"/api/users/{self.root.id}/", {"is_active": False})
        self.assertEqual(patch_resp.status_code, status.HTTP_403_FORBIDDEN)
        del_resp = self.client.delete(f"/api/users/{self.root.id}/")
        self.assertEqual(del_resp.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(User.objects.get(pk=self.root.pk).is_active)

    def test_teacher_can_still_list_superusers_and_manage_students(self):
        self._as(self.teacher)
        self.assertEqual(self.client.get(f"/api/users/{self.root.id}/").status_code, 200)
        resp = self.client.post(
            f"/api/users/{self.student.id}/reset-password/", {"password": "New-Student-Pass-7"}
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_superuser_can_modify_superuser(self):
        other_root = User.objects.create_superuser(username="root2", password=STRONG)
        self._as(self.root)
        resp = self.client.post(
            f"/api/users/{other_root.id}/reset-password/", {"password": "Root-Reset-Pass-4"}
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    # --- no self-lockout --------------------------------------------------

    def test_admin_cannot_demote_or_deactivate_self(self):
        self._as(self.teacher)
        demote = self.client.patch(f"/api/users/{self.teacher.id}/", {"role": "student"})
        self.assertEqual(demote.status_code, status.HTTP_400_BAD_REQUEST)
        deactivate = self.client.patch(f"/api/users/{self.teacher.id}/", {"is_active": False})
        self.assertEqual(deactivate.status_code, status.HTTP_400_BAD_REQUEST)
        self.teacher.refresh_from_db()
        self.assertEqual(self.teacher.role, User.Role.ADMIN)
        self.assertTrue(self.teacher.is_active)

    # --- reset-password runs the validators -------------------------------

    def test_reset_password_rejects_weak_passwords(self):
        self._as(self.teacher)
        for weak in ("12345678", "password", "qwertyuiop"):
            resp = self.client.post(
                f"/api/users/{self.student.id}/reset-password/", {"password": weak}
            )
            self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST, weak)
        self.student.refresh_from_db()
        self.assertTrue(self.student.check_password(STRONG))

    # --- resets and deactivation end existing sessions --------------------

    def _student_session(self):
        refresh = RefreshToken.for_user(self.student)
        return str(refresh), str(refresh.access_token)

    def _session_still_works(self, refresh, access):
        api = APIClient()
        api.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        me = api.get("/api/auth/me/").status_code
        renewed = APIClient().post("/api/auth/refresh/", {"refresh": refresh}).status_code
        return me, renewed

    def test_password_reset_revokes_sessions(self):
        refresh, access = self._student_session()
        self.assertEqual(self._session_still_works(refresh, access), (200, 200))

        refresh, access = self._student_session()
        self._as(self.teacher)
        self.client.post(
            f"/api/users/{self.student.id}/reset-password/", {"password": "Fresh-Student-Pass-3"}
        )
        self.assertEqual(self._session_still_works(refresh, access), (401, 401))

    def test_deactivation_revokes_sessions(self):
        refresh, access = self._student_session()
        self._as(self.teacher)
        resp = self.client.patch(f"/api/users/{self.student.id}/", {"is_active": False})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(self._session_still_works(refresh, access), (401, 401))
