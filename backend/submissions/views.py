from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle

from accounts.permissions import IsAdmin

from .models import Submission
from .serializers import SubmissionCreateSerializer, SubmissionSerializer


class SubmissionRateThrottle(UserRateThrottle):
    scope = "submissions"


class SubmissionViewSet(
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

        problem_id = self.request.query_params.get("problem")
        if problem_id:
            qs = qs.filter(problem_id=problem_id)

        contest_id = self.request.query_params.get("contest")
        if contest_id:
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
        if self.action == "rejudge":
            return [IsAuthenticated(), IsAdmin()]
        return [IsAuthenticated()]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        submission = serializer.save()

        from judge.tasks import judge_submission

        judge_submission.delay(submission.id)

        output = SubmissionSerializer(submission, context={"request": request})
        return Response(output.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="rejudge")
    def rejudge(self, request, pk=None):
        submission = self.get_object()
        submission.status = Submission.Status.PENDING
        submission.compile_error = ""
        submission.judged_at = None
        submission.save(update_fields=["status", "compile_error", "judged_at"])
        submission.results.all().delete()

        from judge.tasks import judge_submission

        judge_submission.delay(submission.id)
        output = SubmissionSerializer(submission, context={"request": request})
        return Response(output.data)
