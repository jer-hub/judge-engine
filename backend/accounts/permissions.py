from rest_framework.permissions import BasePermission


class IsAdmin(BasePermission):
    """Allow only platform admins / teachers."""

    def has_permission(self, request, view) -> bool:
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and getattr(user, "is_platform_admin", False)
        )
