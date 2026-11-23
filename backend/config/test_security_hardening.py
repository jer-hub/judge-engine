from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase, TestCase

from config.security import validate_redis_url_for_production


class ProductionRedisValidationTests(SimpleTestCase):
    def test_rejects_unauthenticated_redis_url(self):
        with self.assertRaises(ImproperlyConfigured):
            validate_redis_url_for_production("redis://redis:6379/0", "REDIS_URL")

    def test_rejects_published_dev_redis_password(self):
        with self.assertRaises(ImproperlyConfigured):
            validate_redis_url_for_production(
                "redis://:judge_dev_redis_password@redis:6379/0", "REDIS_URL"
            )

    def test_rejects_short_redis_password(self):
        with self.assertRaises(ImproperlyConfigured):
            validate_redis_url_for_production(
                "redis://:short123@redis:6379/0", "CELERY_BROKER_URL"
            )

    def test_accepts_strong_password_for_redis_and_rediss(self):
        validate_redis_url_for_production(
            "redis://:S3cureRandomRedisPass_2026_Strong!@redis:6379/0",
            "REDIS_URL",
        )
        validate_redis_url_for_production(
            "rediss://default:S3cureRandomRedisPass_2026_Strong!@redis.internal:6379/1",
            "CELERY_RESULT_BACKEND",
        )


class AdminCspHeaderTests(TestCase):
    def test_django_admin_login_sets_csp_header(self):
        resp = self.client.get("/admin/login/")
        self.assertEqual(resp.status_code, 200)
        csp = resp.headers.get("Content-Security-Policy", "")
        self.assertIn("default-src 'self'", csp)
        self.assertIn("object-src 'none'", csp)
        self.assertIn("frame-ancestors 'none'", csp)

    def test_json_api_response_keeps_clean_headers(self):
        resp = self.client.get("/api/auth/me/")
        self.assertIn(resp.status_code, (401, 403))
        csp = resp.headers.get("Content-Security-Policy", "")
        self.assertIn("frame-ancestors 'none'", csp)
