from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework.test import APITestCase

User = get_user_model()


class LoginThrottleTests(APITestCase):
    """The Next.js proxy forwards the client IP as X-Forwarded-For."""

    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        for name in ("alice", "bob"):
            User.objects.create_user(username=name, password="pass12345")

    def _login(self, username, ip, password="wrong-password"):
        return self.client.post(
            "/api/auth/login/",
            {"username": username, "password": password},
            format="json",
            HTTP_X_FORWARDED_FOR=ip,
        )

    def test_students_on_different_ips_do_not_share_a_bucket(self):
        # 40 students logging in at contest start, all via the same frontend.
        for i in range(40):
            User.objects.create_user(username=f"s{i}", password="pass12345")
            resp = self._login(f"s{i}", f"10.0.0.{i + 1}", password="pass12345")
            self.assertEqual(resp.status_code, 200, f"student {i}")

    def test_username_is_capped_across_ips(self):
        codes = [self._login("alice", f"10.0.1.{i}").status_code for i in range(1, 7)]
        self.assertEqual(codes[:5], [401] * 5)
        self.assertEqual(codes[5], 429)
        # Another account from a fresh IP is unaffected.
        self.assertEqual(self._login("bob", "10.0.2.1").status_code, 401)

    def test_successful_logins_do_not_count_toward_the_username_cap(self):
        # A student re-signing in on several lab PCs is never locked out.
        for i in range(1, 9):
            resp = self._login("alice", f"10.0.3.{i}", password="pass12345")
            self.assertEqual(resp.status_code, 200, f"login {i}")
        # Failures still count after them.
        codes = [self._login("alice", f"10.0.4.{i}").status_code for i in range(1, 7)]
        self.assertEqual(codes, [401] * 5 + [429])
