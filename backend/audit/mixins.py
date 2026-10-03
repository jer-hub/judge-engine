"""Record admins' API writes in the audit log, from any DRF viewset."""
from __future__ import annotations

import logging

from .models import AuditEvent

logger = logging.getLogger("django.request")

WRITE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})
# Response fields that name the object, for a readable target.
_LABEL_KEYS = ("username", "title", "slug")


class AuditedViewSetMixin:
    """Log every successful admin write: create/update/delete and custom
    actions (reveal, bulk rejudge, password resets...). Students' own writes
    (submitting, registering, asking) are not audit material."""

    audit_name: str = ""

    def perform_destroy(self, instance):
        # The object is gone by the time the response is finalized.
        self._audit_label = str(instance)
        super().perform_destroy(instance)

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        try:
            self._record_audit(request, response, kwargs)
        except Exception:
            # Auditing must never turn a successful request into an error.
            logger.exception("Could not write audit event")
        return response

    def _record_audit(self, request, response, kwargs):
        user = getattr(request, "user", None)
        if (
            request.method not in WRITE_METHODS
            or response.status_code >= 400
            or not getattr(user, "is_platform_admin", False)
        ):
            return
        name = self.audit_name or getattr(self, "basename", "") or type(self).__name__
        action = f"{name}.{getattr(self, 'action', None) or request.method.lower()}"
        body = request.data if hasattr(request.data, "keys") else {}
        if body.get("dry_run") is True:
            action += ".dry_run"  # a preview changed nothing
        key = kwargs.get("pk") or kwargs.get("slug") or ""
        label = getattr(self, "_audit_label", "")
        data = response.data if isinstance(getattr(response, "data", None), dict) else {}
        if not label:
            label = next((str(data[k]) for k in _LABEL_KEYS if data.get(k)), "")
        target = f"{name}:{key}" if key else name
        if label:
            target = f"{target} ({label})"
        AuditEvent.objects.create(
            actor=user,
            actor_username=user.username,
            action=action[:64],
            target=target[:200],
            fields=sorted(str(k) for k in body.keys())[:50],
            status_code=response.status_code,
        )
