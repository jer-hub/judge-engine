from django.db import connection
from django.http import JsonResponse


def healthz(request):
    """Liveness for the container healthcheck: the app is up and reaches the DB."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    except Exception:
        return JsonResponse({"ok": False}, status=503)
    return JsonResponse({"ok": True})
