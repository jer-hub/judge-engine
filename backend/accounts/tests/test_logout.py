from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework.test import APITestCase
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()


class LogoutTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)

    def test_a_whole_lab_behind_one_ip_can_log_out(self):
        # 40 students on NAT log out at the bell; every token must be revoked.
        for i in range(40):
            user = User.objects.create_user(username=f"lab{i}", password="pass12345")
            resp = self.client.post(
                "/api/auth/logout/",
                {"refresh": str(RefreshToken.for_user(user))},
                format="json",
                HTTP_X_FORWARDED_FOR="10.0.0.1",
            )
            self.assertEqual(resp.status_code, 205, f"student {i}")
        self.assertEqual(BlacklistedToken.objects.count(), 40)

    def test_invalid_token_is_rejected(self):
        resp = self.client.post("/api/auth/logout/", {"refresh": "junk"}, format="json")
        self.assertEqual(resp.status_code, 400)
