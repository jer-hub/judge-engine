from django.http import HttpResponse
from django.utils import timezone
from django.utils.text import slugify
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle

from accounts.permissions import IsAdmin
from audit.mixins import AuditedViewSetMixin

from .export import MAX_EXPORT_SUBMISSIONS, solutions_zip
from .models import Submission
from .rejudge import queue_rejudge
from .serializers import SubmissionCreateSerializer, SubmissionSerializer


def _int_param(data, name: str) -> int | None:
    """An optional integer id from query params or a body; 400 if malformed."""
    value = data.get(name)
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        raise ValidationError({name: "Must be an integer id."}) from None


class SubmissionRateThrottle(UserRateThrottle):
    scope = "submissions"


class SubmissionViewSet(
    AuditedViewSetMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [IsAuthenticated]
    throttle_classes = []

    def get_throttles(self):
        if self.action == "create":
            return [SubmissionRateThrottle()]
        return []

    def get_queryset(self):
        qs = Submission.objects.select_related(
            "user", "problem", "contest"
        ).prefetch_related("results__test_case")
        user = self.request.user
        if not getattr(user, "is_platform_admin", False):
            qs = qs.filter(user=user)

        problem_id = _int_param(self.request.query_params, "problem")
        if problem_id is not None:
            qs = qs.filter(problem_id=problem_id)

        contest_id = _int_param(self.request.query_params, "contest")
        if contest_id is not None:
            qs = qs.filter(contest_id=contest_id)

        me = self.request.query_params.get("user")
        if me == "me":
            qs = qs.filter(user=user)

        return qs

    def get_serializer_class(self):
        if self.action == "create":
            return SubmissionCreateSerializer
        return SubmissionSerializer

    def get_permissions(self):
        if self.action in ("rejudge", "bulk_rejudge", "export"):
            return [IsAuthenticated(), IsAdmin()]
        return [IsAuthenticated()]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        submission = serializer.save()

        from judge.tasks import enqueue_judging

        # Never 500 once the submission is saved: if the broker is down it
        # stays Pending and the recovery sweep queues it later.
        enqueue_judging(submission.id)

        output = SubmissionSerializer(submission, context={"request": request})
        return Response(output.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="rejudge")
    def rejudge(self, request, pk=None):
        submission = self.get_object()
        in_flight = submission.status in (
            Submission.Status.PENDING,
            Submission.Status.JUDGING,
        )
        # ?force=true recovers a submission stuck after a worker crash.
        if in_flight and request.query_params.get("force") != "true":
            return Response(
                {"detail": "Submission is already queued or being judged."},
                status=status.HTTP_409_CONFLICT,
            )
        queue_rejudge(Submission.objects.filter(pk=submission.pk), include_in_flight=True)
        submission.refresh_from_db()
        output = SubmissionSerializer(submission, context={"request": request})
        return Response(output.data)

    @action(detail=False, methods=["post"], url_path="bulk-rejudge")
    def bulk_rejudge(self, request):
        """Re-judge every finished submission to a problem and/or contest,
        e.g. after its test cases were fixed. Pending/Judging ones are left
        alone (they will use the current tests anyway)."""
        problem_id = _int_param(request.data, "problem")
        contest_id = _int_param(request.data, "contest")
        if problem_id is None and contest_id is None:
            raise ValidationError({"detail": "Give a problem, a contest, or both."})
        scope = Submission.objects.all()
        if problem_id is not None:
            scope = scope.filter(problem_id=problem_id)
        if contest_id is not None:
            scope = scope.filter(contest_id=contest_id)
        queued = queue_rejudge(scope)
        return Response(
            {"queued": len(queued), "skipped_in_flight": scope.count() - len(queued)}
        )

    @action(detail=False, methods=["get"], url_path="export")
    def export(self, request):
        """Every submitted solution for a contest and/or problem as a ZIP:
        .java files per student and problem plus index.csv. Optional
        ?section= limits it to one class section."""
        from contests.models import Contest, ContestProblem
        from problems.models import Problem

        problem_id = _int_param(request.query_params, "problem")
        contest_id = _int_param(request.query_params, "contest")
        if problem_id is None and contest_id is None:
            raise ValidationError({"detail": "Give a problem, a contest, or both."})
        scope = Submission.objects.all()
        names, letters = [], {}
        if contest_id is not None:
            contest = Contest.objects.filter(pk=contest_id).first()
            if contest is None:
                raise ValidationError({"contest": "No such contest."})
            scope = scope.filter(contest_id=contest_id)
            names.append(slugify(contest.title) or f"contest-{contest_id}")
            letters = dict(
                ContestProblem.objects.filter(contest_id=contest_id).values_list("problem_id", "letter")
            )
        if problem_id is not None:
            problem = Problem.objects.filter(pk=problem_id).first()
            if problem is None:
                raise ValidationError({"problem": "No such problem."})
            scope = scope.filter(problem_id=problem_id)
            names.append(problem.slug)
        section = (request.query_params.get("section") or "").strip()
        if section:
            scope = scope.filter(user__class_section__iexact=section)
            names.append(slugify(section))
        count = scope.count()
        if count == 0:
            raise ValidationError({"detail": "No submissions to export."})
        if count > MAX_EXPORT_SUBMISSIONS:
            raise ValidationError(
                {"detail": f"{count} submissions; export at most {MAX_EXPORT_SUBMISSIONS} at a time "
                           "(pick a problem or a section)."}
            )
        stamp = timezone.localtime().strftime("%Y%m%d-%H%M")
        response = HttpResponse(solutions_zip(scope, letters), content_type="application/zip")
        response["Content-Disposition"] = (
            f'attachment; filename="{"-".join(names)}-solutions-{stamp}.zip"'
        )
        return response
