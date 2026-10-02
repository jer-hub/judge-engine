from unittest.mock import patch

from django.test import TestCase


class HealthzTests(TestCase):
    def test_healthy_when_db_and_redis_answer(self):
        with patch("config.health.redis.from_url") as from_url:
            from_url.return_value.ping.return_value = True
            resp = self.client.get("/healthz/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), {"ok": True, "db": True, "redis": True})

    def test_unhealthy_when_redis_is_down(self):
        with patch("config.health.redis.from_url") as from_url:
            from_url.return_value.ping.side_effect = ConnectionError("refused")
            resp = self.client.get("/healthz/")
        self.assertEqual(resp.status_code, 503)
        self.assertEqual(resp.json()["redis"], False)
