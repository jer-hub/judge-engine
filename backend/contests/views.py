from django.db.models import Q
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.permissions import IsAdmin

from .models import Contest, ContestParticipant
from .scoreboard import build_scoreboard
from .serializers import (
    ContestDetailSerializer,
    ContestListSerializer,
    ContestWriteSerializer,
)


class ContestViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Contest.objects.all().prefetch_related(
            "contest_problems__problem",
            "participants__user",
        )
        user = self.request.user
        if not getattr(user, "is_platform_admin", False):
            qs = qs.filter(Q(is_public=True) | Q(participants__user=user)).distinct()

        status_filter = self.request.query_params.get("status")
        now = timezone.now()
        if status_filter == "upcoming":
            qs = qs.filter(start_time__gt=now)
        elif status_filter == "active":
            qs = qs.filter(start_time__lte=now, end_time__gte=now)
        elif status_filter == "past":
            qs = qs.filter(end_time__lt=now)
        return qs

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return ContestWriteSerializer
        if self.action == "retrieve":
            return ContestDetailSerializer
        return ContestListSerializer

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [IsAuthenticated(), IsAdmin()]
        return [IsAuthenticated()]

    @action(detail=True, methods=["post"], url_path="register")
    def register(self, request, pk=None):
        contest = self.get_object()
        now = timezone.now()
        if now > contest.end_time:
            return Response(
                {"detail": "Contest has already ended."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        _, created = ContestParticipant.objects.get_or_create(
            contest=contest,
            user=request.user,
        )
        return Response(
            {"registered": True, "created": created},
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    @action(detail=True, methods=["get"], url_path="scoreboard")
    def scoreboard(self, request, pk=None):
        contest = self.get_object()
        data = build_scoreboard(contest, viewer=request.user)
        return Response(data)
