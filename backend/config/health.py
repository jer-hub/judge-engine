import redis
from django.conf import settings
from django.db import connection
from django.http import JsonResponse


def healthz(request):
    """Container healthcheck: the app is up and reaches the DB and Redis.

    Redis is the judge queue; without it nothing gets judged, so report it
    rather than look healthy while submissions pile up as Pending.
    """
    checks = {}
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        checks["db"] = True
    except Exception:
        checks["db"] = False
    try:
        checks["redis"] = bool(
            redis.from_url(settings.REDIS_URL, socket_timeout=2, socket_connect_timeout=2).ping()
        )
    except Exception:
        checks["redis"] = False
    ok = all(checks.values())
    return JsonResponse({"ok": ok, **checks}, status=200 if ok else 503)
