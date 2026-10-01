from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import AllowAny
from rest_framework.throttling import AnonRateThrottle, SimpleRateThrottle
from rest_framework_simplejwt.views import TokenObtainPairView


class LoginRateThrottle(AnonRateThrottle):
    """Per client IP. Needs the frontend to forward X-Forwarded-For (see NUM_PROXIES)."""

    scope = "login"


class LoginUsernameRateThrottle(SimpleRateThrottle):
    """Per target username, so brute force on one account is capped even when
    requests come from many IPs (or one spoofed X-Forwarded-For).

    Only failed logins count: the view records them via ``record_failure``,
    so a student who signs in successfully again and again is never throttled.
    """

    scope = "login-user"

    def get_cache_key(self, request, view):
        username = request.data.get("username") if hasattr(request, "data") else None
        if not isinstance(username, str) or not username.strip():
            return None
        return self.cache_format % {
            "scope": self.scope,
            "ident": username.strip().lower(),
        }

    def allow_request(self, request, view):
        if self.rate is None:
            return True
        self.key = self.get_cache_key(request, view)
        if self.key is None:
            return True
        self.history = self.cache.get(self.key, [])
        self.now = self.timer()
        while self.history and self.history[-1] <= self.now - self.duration:
            self.history.pop()
        if len(self.history) >= self.num_requests:
            return self.throttle_failure()
        # Unlike SimpleRateThrottle, do not record this request yet.
        return True

    def record_failure(self):
        if self.rate is None or self.key is None:
            return
        self.history.insert(0, self.now)
        self.cache.set(self.key, self.history, self.duration)


class ThrottledTokenObtainPairView(TokenObtainPairView):
    permission_classes = [AllowAny]
    throttle_classes = [LoginRateThrottle, LoginUsernameRateThrottle]

    def post(self, request, *args, **kwargs):
        try:
            return super().post(request, *args, **kwargs)
        except AuthenticationFailed:
            for throttle in self._throttles:
                if isinstance(throttle, LoginUsernameRateThrottle):
                    throttle.record_failure()
            raise

    def get_throttles(self):
        # Keep the instances check_throttles() used, so post() can record
        # the failure on the same history it checked.
        self._throttles = super().get_throttles()
        return self._throttles
