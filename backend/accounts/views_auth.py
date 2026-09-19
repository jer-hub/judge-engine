from rest_framework.permissions import AllowAny
from rest_framework.throttling import AnonRateThrottle
from rest_framework_simplejwt.views import TokenObtainPairView


class LoginRateThrottle(AnonRateThrottle):
    scope = "login"


class ThrottledTokenObtainPairView(TokenObtainPairView):
    permission_classes = [AllowAny]
    throttle_classes = [LoginRateThrottle]
