from django.conf import settings
from rest_framework import serializers

from problems.models import Problem
from submissions.models import Submission


class RunPreviewSerializer(serializers.Serializer):
    problem = serializers.PrimaryKeyRelatedField(queryset=Problem.objects.all())
    source_code = serializers.CharField()
    language = serializers.ChoiceField(choices=Submission.Language.choices)
    stdin = serializers.CharField(required=False, allow_blank=True, default="")

    def validate_source_code(self, value: str) -> str:
        max_bytes = settings.JUDGE_SOURCE_MAX_BYTES
        if len(value.encode("utf-8")) > max_bytes:
            raise serializers.ValidationError(
                f"Source code exceeds {max_bytes} byte limit."
            )
        if not value.strip():
            raise serializers.ValidationError("Source code cannot be empty.")
        return value

    def validate_stdin(self, value: str) -> str:
        max_bytes = settings.JUDGE_STDIN_MAX_BYTES
        if len(value.encode("utf-8")) > max_bytes:
            raise serializers.ValidationError(
                f"Stdin exceeds {max_bytes} byte limit."
            )
        return value

    def validate_language(self, value: str) -> str:
        if value != Submission.Language.JAVA:
            raise serializers.ValidationError("Only Java is supported in v1.")
        return value

    def validate_problem(self, problem: Problem) -> Problem:
        user = self.context["request"].user
        if problem.is_published or getattr(user, "is_platform_admin", False):
            return problem
        from contests.access import user_can_access_unpublished_problem

        if user_can_access_unpublished_problem(user, problem):
            return problem
        raise serializers.ValidationError("Problem is not published.")
