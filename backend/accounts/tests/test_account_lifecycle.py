from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()


class StaffFollowsRoleTests(APITestCase):
    def test_demoted_admin_loses_django_admin_access(self):
        teacher = User.objects.create_user(
            username="t", password="pass12345", role=User.Role.ADMIN
        )
        self.assertTrue(teacher.is_staff)
        teacher.role = User.Role.STUDENT
        teacher.save()
        self.assertFalse(teacher.is_staff)

    def test_superuser_keeps_staff(self):
        root = User.objects.create_superuser(username="root", password="pass12345")
        root.save()
        self.assertTrue(root.is_staff)


class DeletedUserTokenTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="a", password="pass12345", role=User.Role.ADMIN
        )
        self.student = User.objects.create_user(username="s", password="pass12345")

    def _refresh(self, token):
        return self.client.post("/api/auth/refresh/", {"refresh": str(token)}, format="json")

    def test_deleting_a_user_ends_their_sessions(self):
        token = RefreshToken.for_user(self.student)
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(self.admin).access_token}"
        )
        self.assertEqual(self.client.delete(f"/api/users/{self.student.id}/").status_code, 204)
        self.client.credentials()
        self.assertEqual(self._refresh(token).status_code, 401)

    def test_refresh_for_a_vanished_user_is_401_not_500(self):
        token = RefreshToken.for_user(self.student)
        User.objects.filter(pk=self.student.pk).delete()  # e.g. via Django admin
        self.assertEqual(self._refresh(token).status_code, 401)
