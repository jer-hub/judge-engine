from django.db.models import Q
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.permissions import IsAdmin
from contests.access import unpublished_contest_problem_q
from submissions.models import Submission

from .models import Problem
from .queries import multi_tag_q, search_q
from .serializers import (
    ProblemAdminListSerializer,
    ProblemDetailSerializer,
    ProblemListSerializer,
    ProblemUpdateSerializer,
    ProblemWriteSerializer,
    annotate_admin_list,
)


class ProblemViewSet(viewsets.ModelViewSet):
    lookup_field = "slug"
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        is_admin = getattr(user, "is_platform_admin", False)

        if self.action == "retrieve":
            qs = Problem.objects.all().prefetch_related("test_cases").order_by("title")
        elif self.action == "list" and is_admin:
            qs = annotate_admin_list(Problem.objects.all())
        else:
            qs = Problem.objects.all().order_by("title")

        if not is_admin:
            if self.action == "retrieve":
                qs = qs.filter(Q(is_published=True) | unpublished_contest_problem_q(user))
            else:
                qs = qs.filter(is_published=True)

        difficulty = self.request.query_params.get("difficulty")
        if difficulty:
            qs = qs.filter(difficulty=difficulty)

        tag = self.request.query_params.get("tag")
        if tag:
            qs = qs.filter(multi_tag_q(tag))

        search = self.request.query_params.get("search")
        if search:
            qs = qs.filter(search_q(search))

        if is_admin:
            published = self.request.query_params.get("is_published")
            if published is not None and published != "":
                truthy = published.lower() in ("1", "true", "yes")
                qs = qs.filter(is_published=truthy)

        return qs

    def get_serializer_class(self):
        if self.action == "create":
            return ProblemWriteSerializer
        if self.action in ("update", "partial_update"):
            return ProblemUpdateSerializer
        if self.action == "retrieve":
            return ProblemDetailSerializer
        user = self.request.user
        if getattr(user, "is_platform_admin", False):
            return ProblemAdminListSerializer
        return ProblemListSerializer

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [IsAuthenticated(), IsAdmin()]
        return [IsAuthenticated()]

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if Submission.objects.filter(problem=instance).exists():
            return Response(
                {
                    "detail": (
                        "Cannot delete a problem that has submissions. "
                        "Unpublish it instead, or remove submissions via Django Admin."
                    )
                },
                status=status.HTTP_409_CONFLICT,
            )
        return super().destroy(request, *args, **kwargs)
