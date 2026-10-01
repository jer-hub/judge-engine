from rest_framework.permissions import AllowAny
from rest_framework.throttling import AnonRateThrottle, SimpleRateThrottle
from rest_framework_simplejwt.views import TokenObtainPairView


class LoginRateThrottle(AnonRateThrottle):
    """Per client IP. Needs the frontend to forward X-Forwarded-For (see NUM_PROXIES)."""

    scope = "login"


class LoginUsernameRateThrottle(SimpleRateThrottle):
    """Per target username, so brute force on one account is capped even when
    requests come from many IPs (or one spoofed X-Forwarded-For)."""

    scope = "login-user"

    def get_cache_key(self, request, view):
        username = request.data.get("username") if hasattr(request, "data") else None
        if not isinstance(username, str) or not username.strip():
            return None
        return self.cache_format % {
            "scope": self.scope,
            "ident": username.strip().lower(),
        }


class ThrottledTokenObtainPairView(TokenObtainPairView):
    permission_classes = [AllowAny]
    throttle_classes = [LoginRateThrottle, LoginUsernameRateThrottle]
