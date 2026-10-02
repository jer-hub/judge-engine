from rest_framework import generics, serializers
from rest_framework.permissions import IsAuthenticated

from accounts.permissions import IsAdmin

from .models import AuditEvent


class AuditEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditEvent
        fields = ("id", "actor_username", "action", "target", "fields", "status_code", "created_at")


class AuditEventListView(generics.ListAPIView):
    """Admin: the audit trail, newest first. ?actor= and ?action= filter
    (action matches a prefix, e.g. "user." or "contest.reveal")."""

    permission_classes = [IsAuthenticated, IsAdmin]
    serializer_class = AuditEventSerializer

    def get_queryset(self):
        qs = AuditEvent.objects.all()
        actor = self.request.query_params.get("actor", "").strip()
        if actor:
            qs = qs.filter(actor_username__iexact=actor)
        action = self.request.query_params.get("action", "").strip()
        if action:
            qs = qs.filter(action__startswith=action)
        return qs
