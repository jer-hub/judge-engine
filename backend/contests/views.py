from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.text import slugify
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.permissions import IsAdmin

from .export import standings_csv
from . import clarifications as clar
from .models import Clarification, Contest, ContestParticipant
from .scoreboard import build_scoreboard, invalidate_scoreboard_cache
from .similarity import contest_similarity
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
        if self.action in (
            "create", "update", "partial_update", "destroy",
            "reveal", "extensions", "standings_export", "answer_clarification",
            "similarity",
        ):
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

    @action(detail=True, methods=["get", "post"], url_path="clarifications")
    def clarifications(self, request, pk=None):
        """GET: what the viewer may see. POST: a student asks a question
        ({"question", "problem_letter"?}); an admin posts an announcement
        ({"answer"})."""
        contest = self.get_object()
        if request.method == "POST":
            if getattr(request.user, "is_platform_admin", False):
                item = clar.announce(contest, request.user, request.data)
            else:
                item = clar.ask_question(contest, request.user, request.data)
            return Response(
                clar.ClarificationSerializer(item, context={"request": request}).data,
                status=status.HTTP_201_CREATED,
            )
        items = clar.visible_clarifications(contest, request.user)
        return Response(
            clar.ClarificationSerializer(items, many=True, context={"request": request}).data
        )

    @action(
        detail=True,
        methods=["post"],
        url_path=r"clarifications/(?P<clarification_id>\d+)/answer",
    )
    def answer_clarification(self, request, pk=None, clarification_id=None):
        """Admin: answer a question ({"answer", "is_public"}); is_public shows
        it to every contestant."""
        contest = self.get_object()
        item = get_object_or_404(Clarification, pk=clarification_id, contest=contest)
        item = clar.answer(item, request.user, request.data)
        return Response(clar.ClarificationSerializer(item, context={"request": request}).data)

    @action(detail=True, methods=["get"], url_path="similarity")
    def similarity(self, request, pk=None):
        """Admin: pairs of students with suspiciously similar code per problem
        (?threshold=0.6, from 0.3 to 1). A lead to review, not proof."""
        contest = self.get_object()
        try:
            threshold = float(request.query_params.get("threshold", 0.6))
        except ValueError:
            raise ValidationError({"threshold": "Must be a number."}) from None
        if not 0.3 <= threshold <= 1:
            raise ValidationError({"threshold": "Must be between 0.3 and 1."})
        return Response({"threshold": threshold, "pairs": contest_similarity(contest, threshold)})

    @action(detail=True, methods=["post"], url_path="reveal")
    def reveal(self, request, pk=None):
        """Admin: lift the scoreboard freeze now ({"revealed": true}), or
        freeze it again ({"revealed": false})."""
        contest = self.get_object()
        revealed = request.data.get("revealed", True)
        if not isinstance(revealed, bool):
            raise ValidationError({"revealed": "Must be true or false."})
        contest.results_revealed_at = timezone.now() if revealed else None
        contest.save(update_fields=["results_revealed_at"])
        invalidate_scoreboard_cache(contest.id)
        return Response(ContestDetailSerializer(contest, context={"request": request}).data)

    @action(detail=True, methods=["post"], url_path="extensions")
    def extensions(self, request, pk=None):
        """Admin: give a registered student extra minutes ({"username",
        "extra_minutes"}; 0 removes the extension)."""
        contest = self.get_object()
        username = request.data.get("username")
        extra = request.data.get("extra_minutes")
        if not isinstance(username, str) or not username.strip():
            raise ValidationError({"username": "Required."})
        if isinstance(extra, bool) or not isinstance(extra, int) or not 0 <= extra <= 24 * 60:
            raise ValidationError({"extra_minutes": "Whole minutes from 0 to 1440."})
        participant = (
            ContestParticipant.objects.filter(contest=contest, user__username__iexact=username.strip())
            .select_related("user")
            .first()
        )
        if participant is None:
            raise ValidationError({"username": "Not registered for this contest."})
        participant.extra_minutes = extra
        participant.save(update_fields=["extra_minutes"])
        invalidate_scoreboard_cache(contest.id)
        return Response(
            {
                "username": participant.user.username,
                "extra_minutes": participant.extra_minutes,
                "ends_at": contest.end_time_for(participant.user).isoformat(),
            }
        )

    @action(detail=True, methods=["get"], url_path="scoreboard")
    def scoreboard(self, request, pk=None):
        contest = self.get_object()
        data = build_scoreboard(contest, viewer=request.user)
        return Response(data)

    @action(detail=True, methods=["get"], url_path="standings-export")
    def standings_export(self, request, pk=None):
        """Admin: final standings as CSV; ?section= keeps one class section."""
        contest = self.get_object()
        section = request.query_params.get("section", "").strip() or None
        body = standings_csv(contest, viewer=request.user, section=section)
        name = slugify(contest.title) or f"contest-{contest.id}"
        if section:
            name += f"-{slugify(section) or 'section'}"
        response = HttpResponse(body, content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = f'attachment; filename="{name}-standings.csv"'
        return response
