from django.conf import settings
from django.db import models


class AuditEvent(models.Model):
    """One admin write through the API: who, what, when. Field names only,
    never values, so passwords and source code never land here."""

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_events",
    )
    # Kept as text so the trail survives the actor's account being deleted.
    actor_username = models.CharField(max_length=150)
    action = models.CharField(max_length=64, db_index=True)
    target = models.CharField(max_length=200, blank=True, default="")
    fields = models.JSONField(default=list, blank=True)
    status_code = models.PositiveSmallIntegerField()
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self) -> str:
        return f"{self.actor_username} {self.action} {self.target}"
