"""Ending a user's existing sessions (refresh tokens) server-side."""
from rest_framework_simplejwt.token_blacklist.models import (
    BlacklistedToken,
    OutstandingToken,
)


def revoke_user_sessions(user) -> int:
    """Blacklist every outstanding refresh token for ``user``.

    Access tokens die on their own: SIMPLE_JWT.CHECK_REVOKE_TOKEN rejects them
    after a password change, and CHECK_USER_IS_ACTIVE after deactivation.
    """
    tokens = OutstandingToken.objects.filter(
        user=user, blacklistedtoken__isnull=True
    )
    created = BlacklistedToken.objects.bulk_create(
        [BlacklistedToken(token=t) for t in tokens], ignore_conflicts=True
    )
    return len(created)
