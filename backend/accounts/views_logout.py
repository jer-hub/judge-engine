from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken


class LogoutRateThrottle(UserRateThrottle):
    scope = "logout"


class LogoutAnonRateThrottle(AnonRateThrottle):
    scope = "logout"


class LogoutView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [LogoutRateThrottle, LogoutAnonRateThrottle]

    def post(self, request):
        refresh = request.data.get("refresh")
        if not refresh:
            return Response(
                {"detail": "Invalid or expired token."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            token = RefreshToken(refresh)
            if request.user and request.user.is_authenticated:
                token_user_id = token.get("user_id")
                if token_user_id is not None and int(token_user_id) != int(request.user.id):
                    return Response(
                        {"detail": "Invalid or expired token."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
            token.blacklist()
        except (TokenError, ValueError, TypeError):
            return Response(
                {"detail": "Invalid or expired token."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response({"detail": "Logged out."}, status=status.HTTP_205_RESET_CONTENT)
