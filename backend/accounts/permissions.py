from rest_framework.permissions import SAFE_METHODS, BasePermission


class IsAdmin(BasePermission):
    """Allow only platform admins / teachers."""

    def has_permission(self, request, view) -> bool:
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and getattr(user, "is_platform_admin", False)
        )


class CanModifyTargetUser(BasePermission):
    """Teacher-role admins manage the roster, but only a superuser may change
    or delete a superuser — otherwise any teacher could reset the bootstrap
    superuser's password and take over Django admin."""

    message = "Only a superuser can modify a superuser account."

    def has_object_permission(self, request, view, obj) -> bool:
        if request.method in SAFE_METHODS:
            return True
        return not obj.is_superuser or request.user.is_superuser
