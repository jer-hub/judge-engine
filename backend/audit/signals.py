"""Sign-in events for teacher accounts, the ones worth attacking.

Student logins are not recorded: a class signing in several times a day
would bury the admin writes this log is for.
"""
from __future__ import annotations

import logging

from axes.signals import user_locked_out
from django.contrib.auth import get_user_model
from django.contrib.auth.signals import user_logged_in, user_login_failed
from django.dispatch import receiver

from .models import AuditEvent

logger = logging.getLogger("django.request")


def _staff_account(username: str | None):
    if not username:
        return None
    User = get_user_model()
    user = User.objects.filter(username__iexact=username).first()
    if user is not None and (user.is_platform_admin or user.is_staff):
        return user
    return None


def _record(user, action: str, request, status_code: int) -> None:
    try:
        path = getattr(request, "path", "") or ""
        AuditEvent.objects.create(
            actor=user,
            actor_username=user.username,
            action=action,
            target=path[:200],
            status_code=status_code,
        )
    except Exception:
        logger.exception("Could not write audit event")


@receiver(user_logged_in)
def _logged_in(sender, request, user, **kwargs):
    if user.is_platform_admin or user.is_staff:
        _record(user, "auth.login", request, 200)


@receiver(user_login_failed)
def _login_failed(sender, credentials, request=None, **kwargs):
    user = _staff_account((credentials or {}).get("username"))
    if user is not None:
        _record(user, "auth.login_failed", request, 401)


@receiver(user_locked_out)
def _locked_out(sender, request, username=None, ip_address=None, **kwargs):
    user = _staff_account(username)
    if user is not None:
        _record(user, "auth.locked_out", request, 429)
