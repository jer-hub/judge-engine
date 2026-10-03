from django.contrib.auth.signals import user_logged_in
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import AllowAny
from rest_framework.throttling import AnonRateThrottle, SimpleRateThrottle
from rest_framework_simplejwt.exceptions import InvalidToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView


class LoginRateThrottle(AnonRateThrottle):
    """Per client IP. Needs the frontend to forward X-Forwarded-For (see NUM_PROXIES)."""

    scope = "login"


class LoginUsernameRateThrottle(SimpleRateThrottle):
    """Failed logins per target username, across all IPs, so brute force on
    one account stays capped even from many IPs (or a spoofed
    X-Forwarded-For). Looser than the per-IP cap below, so one attacker
    cannot lock a classmate out just by typing their username wrong.

    Only failed logins count: the view records them via ``record_failure``,
    so a student who signs in successfully again and again is never throttled.
    """

    scope = "login-user"

    def ident(self, request, username: str) -> str:
        return username

    def get_cache_key(self, request, view):
        username = request.data.get("username") if hasattr(request, "data") else None
        if not isinstance(username, str) or not username.strip():
            return None
        return self.cache_format % {
            "scope": self.scope,
            "ident": self.ident(request, username.strip().lower()),
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


class LoginUsernameIpRateThrottle(LoginUsernameRateThrottle):
    """Failed logins per username from one client IP: the tight cap."""

    scope = "login-user-ip"

    def ident(self, request, username: str) -> str:
        return f"{username}|{self.get_ident(request)}"


class ThrottledTokenObtainPairView(TokenObtainPairView):
    permission_classes = [AllowAny]
    throttle_classes = [
        LoginRateThrottle, LoginUsernameIpRateThrottle, LoginUsernameRateThrottle,
    ]

    def post(self, request, *args, **kwargs):
        try:
            response = super().post(request, *args, **kwargs)
        except AuthenticationFailed:
            for throttle in self._throttles:
                if isinstance(throttle, LoginUsernameRateThrottle):
                    throttle.record_failure()
            raise
        if response.status_code == 200:
            # simplejwt sends no login signal; send it like Django's login()
            # does (updates last_login, records teacher sign-ins in the audit).
            from accounts.models import User

            user = User.objects.filter(username=request.data.get("username")).first()
            if user is not None:
                user_logged_in.send(sender=User, request=request, user=user)
        return response

    def get_throttles(self):
        # Keep the instances check_throttles() used, so post() can record
        # the failure on the same history it checked.
        self._throttles = super().get_throttles()
        return self._throttles


class SafeTokenRefreshView(TokenRefreshView):
    """simplejwt looks the user up with .get() and lets DoesNotExist escape
    as a 500 when the account was deleted; that is just an invalid token."""

    def post(self, request, *args, **kwargs):
        from accounts.models import User

        try:
            return super().post(request, *args, **kwargs)
        except User.DoesNotExist as exc:
            raise InvalidToken("User no longer exists.") from exc
