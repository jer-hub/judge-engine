from django.conf import settings
from django.contrib import admin

from .models import Submission, SubmissionResult


class SubmissionResultInline(admin.TabularInline):
    model = SubmissionResult
    extra = 0
    readonly_fields = (
        "test_case",
        "verdict",
        "execution_time_ms",
        "memory_used_kb",
        "stdout_snippet",
        "stderr_snippet",
    )
    can_delete = False


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "problem",
        "contest",
        "status",
        "language",
        "submitted_at",
        "judged_at",
    )
    list_filter = ("status", "language", "contest")
    search_fields = ("user__username", "problem__slug", "problem__title")
    readonly_fields = ("submitted_at", "judged_at")
    inlines = [SubmissionResultInline]

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("user", "problem", "contest")
        )


@admin.register(SubmissionResult)
class SubmissionResultAdmin(admin.ModelAdmin):
    list_display = (
        "submission",
        "test_case",
        "verdict",
        "execution_time_ms",
        "memory_used_kb",
    )
    list_filter = ("verdict",)
