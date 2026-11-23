"""Security validators and response headers for Django."""
from __future__ import annotations

from urllib.parse import urlparse

from django.core.exceptions import ImproperlyConfigured

WEAK_REDIS_PASSWORDS = frozenset(
    {
        "",
        "judge_dev_redis_password",
        "change-me",
        "change-me-strong-redis-password",
        "password",
        "redis",
    }
)

MIN_REDIS_PASSWORD_LEN = 16

BACKEND_CSP = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline'; "
    "style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data:; "
    "font-src 'self' data:; "
    "connect-src 'self'; "
    "object-src 'none'; "
    "base-uri 'self'; "
    "form-action 'self'; "
    "frame-ancestors 'none'"
)


def validate_redis_url_for_production(url: str, setting_name: str) -> None:
    """Reject unauthenticated or weak-password Redis URLs when DEBUG is False."""
    parsed = urlparse(url or "")
    if parsed.scheme not in ("redis", "rediss", "unix"):
        raise ImproperlyConfigured(
            f"{setting_name} must use redis://, rediss://, or unix:// scheme."
        )
    if parsed.scheme == "unix":
        return
    password = parsed.password or ""
    if password in WEAK_REDIS_PASSWORDS or len(password) < MIN_REDIS_PASSWORD_LEN:
        raise ImproperlyConfigured(
            f"{setting_name} must include a strong Redis password "
            f"(>= {MIN_REDIS_PASSWORD_LEN} chars, not the dev default) when DEBUG is False."
        )


class ContentSecurityPolicyMiddleware:
    """Attach a baseline Content-Security-Policy to Django responses (notably /admin/)."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if "Content-Security-Policy" not in response.headers:
            response.headers["Content-Security-Policy"] = BACKEND_CSP
        return response
