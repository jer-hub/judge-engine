from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

User = get_user_model()


# The admin login page renders templates that reference static files; CI does
# not run collectstatic, so skip the manifest lookup.
@override_settings(
    AXES_FAILURE_LIMIT=3,
    STORAGES={
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    },
)
class DjangoAdminLockoutTests(TestCase):
    """The Django admin login has no DRF throttle; django-axes caps it."""

    def setUp(self):
        User.objects.create_superuser(username="teacher", password="pass12345")
        User.objects.create_superuser(username="other", password="pass12345")

    def _login(self, username, password="wrong-password", ip="10.0.0.1"):
        return self.client.post(
            "/admin/login/?next=/admin/",
            {"username": username, "password": password},
            HTTP_X_FORWARDED_FOR=ip,
        )

    def test_repeated_failures_lock_out_even_the_right_password(self):
        codes = [self._login("teacher").status_code for _ in range(3)]
        self.assertEqual(codes, [200, 200, 429])  # form re-shown, then locked
        self.assertEqual(self._login("teacher", "pass12345").status_code, 429)

    def test_lockout_is_per_username_and_ip(self):
        for _ in range(3):
            self._login("teacher")
        # Same account from another machine, and another account here, still work.
        self.assertEqual(self._login("teacher", "pass12345", ip="10.0.0.2").status_code, 302)
        self.assertEqual(self._login("other", "pass12345").status_code, 302)

    def test_success_resets_the_failure_count(self):
        for _ in range(2):
            self._login("teacher")
        self.assertEqual(self._login("teacher", "pass12345").status_code, 302)
        self.client.logout()
        for _ in range(2):
            self._login("teacher")
        self.assertEqual(self._login("teacher", "pass12345").status_code, 302)

    def test_api_login_failures_do_not_count_toward_admin_lockout(self):
        for _ in range(5):
            self.client.post(
                "/api/auth/login/",
                {"username": "teacher", "password": "wrong-password"},
                content_type="application/json",
                HTTP_X_FORWARDED_FOR="10.0.0.1",
            )
        self.assertEqual(self._login("teacher", "pass12345").status_code, 302)
