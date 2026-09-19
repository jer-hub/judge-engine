from django.conf import settings
from django.utils import timezone
from rest_framework import serializers

from contests.models import Contest, ContestParticipant
from problems.models import Problem

from .models import Submission, SubmissionResult


class SubmissionResultSerializer(serializers.ModelSerializer):
    test_case_order = serializers.IntegerField(source="test_case.order", read_only=True)
    is_sample = serializers.BooleanField(source="test_case.is_sample", read_only=True)

    class Meta:
        model = SubmissionResult
        fields = (
            "id",
            "test_case_order",
            "is_sample",
            "verdict",
            "execution_time_ms",
            "memory_used_kb",
        )
        read_only_fields = fields


class SubmissionSerializer(serializers.ModelSerializer):
    results = SubmissionResultSerializer(many=True, read_only=True)
    problem_slug = serializers.CharField(source="problem.slug", read_only=True)
    problem_title = serializers.CharField(source="problem.title", read_only=True)
    username = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = Submission
        fields = (
            "id",
            "problem",
            "problem_slug",
            "problem_title",
            "contest",
            "username",
            "language",
            "status",
            "compile_error",
            "submitted_at",
            "judged_at",
            "results",
            "source_code",
        )
        read_only_fields = (
            "id",
            "problem_slug",
            "problem_title",
            "username",
            "status",
            "compile_error",
            "submitted_at",
            "judged_at",
            "results",
        )

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get("request")
        # Students see their own source; hide others' unless admin
        if request and not getattr(request.user, "is_platform_admin", False):
            if instance.user_id != request.user.id:
                data.pop("source_code", None)
                data.pop("compile_error", None)
            # Hide hidden-test verdict oracle: only sample results for students
            results = data.get("results") or []
            data["results"] = [r for r in results if r.get("is_sample")]
        return data


class SubmissionCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Submission
        fields = ("problem", "contest", "source_code", "language")

    def validate_source_code(self, value: str) -> str:
        max_bytes = settings.JUDGE_SOURCE_MAX_BYTES
        if len(value.encode("utf-8")) > max_bytes:
            raise serializers.ValidationError(
                f"Source code exceeds {max_bytes} byte limit."
            )
        if not value.strip():
            raise serializers.ValidationError("Source code cannot be empty.")
        return value

    def validate_language(self, value: str) -> str:
        if value != Submission.Language.JAVA:
            raise serializers.ValidationError("Only Java is supported in v1.")
        return value

    def validate(self, attrs):
        problem: Problem = attrs["problem"]
        contest: Contest | None = attrs.get("contest")
        user = self.context["request"].user

        if contest is not None:
            now = timezone.now()
            if now < contest.start_time or now > contest.end_time:
                raise serializers.ValidationError(
                    {"contest": "Submissions are only allowed during the contest window."}
                )
            if not ContestParticipant.objects.filter(
                contest=contest, user=user
            ).exists():
                raise serializers.ValidationError(
                    {"contest": "You must register for the contest first."}
                )
            if not contest.contest_problems.filter(problem=problem).exists():
                raise serializers.ValidationError(
                    {"problem": "Problem is not part of this contest."}
                )
        elif not problem.is_published and not getattr(user, "is_platform_admin", False):
            raise serializers.ValidationError({"problem": "Problem is not published."})

        return attrs

    def create(self, validated_data):
        return Submission.objects.create(
            user=self.context["request"].user,
            status=Submission.Status.PENDING,
            **validated_data,
        )
