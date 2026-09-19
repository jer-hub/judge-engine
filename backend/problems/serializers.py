from django.db.models import Count
from rest_framework import serializers

from .models import Problem, TestCase
from .tags import normalize_tags
from .test_case_sync import reconcile_test_cases


class SampleTestCaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestCase
        fields = ("id", "order", "input_data", "expected_output", "points")
        read_only_fields = fields


class TestCaseWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestCase
        fields = (
            "id",
            "order",
            "input_data",
            "expected_output",
            "is_sample",
            "points",
        )


class TestCaseSerializer(serializers.ModelSerializer):
    """Full test case for admin-only CRUD (includes hidden expected_output)."""

    class Meta:
        model = TestCase
        fields = (
            "id",
            "problem",
            "order",
            "input_data",
            "expected_output",
            "is_sample",
            "points",
        )
        read_only_fields = ("id",)


class ProblemListSerializer(serializers.ModelSerializer):
    tags = serializers.SerializerMethodField()

    class Meta:
        model = Problem
        fields = (
            "id",
            "title",
            "slug",
            "difficulty",
            "tags",
            "time_limit_ms",
            "memory_limit_mb",
            "is_published",
        )

    def get_tags(self, obj: Problem) -> list[str]:
        return obj.tag_list


class ProblemAdminListSerializer(ProblemListSerializer):
    test_case_count = serializers.IntegerField(read_only=True)
    created_by_username = serializers.SerializerMethodField()

    class Meta(ProblemListSerializer.Meta):
        fields = ProblemListSerializer.Meta.fields + (
            "test_case_count",
            "run_all_tests",
            "created_by_username",
            "created_at",
        )

    def get_created_by_username(self, obj: Problem) -> str | None:
        if obj.created_by_id is None:
            return None
        return obj.created_by.username


class ProblemDetailSerializer(serializers.ModelSerializer):
    tags = serializers.SerializerMethodField()
    sample_tests = serializers.SerializerMethodField()

    class Meta:
        model = Problem
        fields = (
            "id",
            "title",
            "slug",
            "statement",
            "difficulty",
            "tags",
            "time_limit_ms",
            "memory_limit_mb",
            "is_published",
            "run_all_tests",
            "sample_tests",
        )

    def get_tags(self, obj: Problem) -> list[str]:
        return obj.tag_list

    def get_sample_tests(self, obj: Problem) -> list[dict]:
        samples = obj.test_cases.filter(is_sample=True)
        return SampleTestCaseSerializer(samples, many=True).data


class ProblemWriteSerializer(serializers.ModelSerializer):
    test_cases = TestCaseWriteSerializer(many=True, required=False)

    class Meta:
        model = Problem
        fields = (
            "id",
            "title",
            "slug",
            "statement",
            "difficulty",
            "tags",
            "time_limit_ms",
            "memory_limit_mb",
            "is_published",
            "run_all_tests",
            "test_cases",
        )

    def validate_tags(self, value: str) -> str:
        return normalize_tags(value)

    def validate(self, attrs):
        attrs = super().validate(attrs)
        publishing = attrs.get("is_published")
        if publishing is None and self.instance is not None:
            publishing = self.instance.is_published
        if not publishing:
            return attrs

        incoming_cases = attrs.get("test_cases")
        if incoming_cases is not None:
            count = len(incoming_cases)
        elif self.instance is not None:
            count = self.instance.test_cases.count()
        else:
            count = 0
        if count == 0:
            raise serializers.ValidationError(
                {
                    "is_published": (
                        "Cannot publish a problem with zero test cases. "
                        "Add at least one test case first."
                    )
                }
            )
        return attrs

    def create(self, validated_data):
        test_cases_data = validated_data.pop("test_cases", [])
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            validated_data["created_by"] = request.user
        problem = Problem.objects.create(**validated_data)
        for tc in test_cases_data:
            TestCase.objects.create(problem=problem, **tc)
        return problem

    def update(self, instance, validated_data):
        test_cases_data = validated_data.pop("test_cases", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if test_cases_data is not None:
            reconcile_test_cases(instance, test_cases_data)
        return instance


class ProblemUpdateSerializer(ProblemWriteSerializer):
    """Slug is immutable after create — silently ignore client-supplied values."""

    slug = serializers.SlugField(read_only=True)


def annotate_admin_list(qs):
    return (
        qs.select_related("created_by")
        .annotate(test_case_count=Count("test_cases", distinct=True))
        .order_by("title")
    )
