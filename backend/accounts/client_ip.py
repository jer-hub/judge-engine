from rest_framework.throttling import BaseThrottle


def client_ip(request) -> str:
    """Client IP as the DRF throttles see it: the X-Forwarded-For entry added
    by the one trusted proxy (NUM_PROXIES), else REMOTE_ADDR.

    Works on a plain Django HttpRequest too, which is what django-axes passes.
    """
    return BaseThrottle().get_ident(request)
