from django.contrib import admin

from .models import Problem, TestCase


class TestCaseInline(admin.TabularInline):
    model = TestCase
    extra = 1
    fields = ("order", "is_sample", "points", "input_data", "expected_output")


@admin.register(Problem)
class ProblemAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "slug",
        "difficulty",
        "is_published",
        "time_limit_ms",
        "memory_limit_mb",
        "created_by",
    )
    list_filter = ("difficulty", "is_published")
    search_fields = ("title", "slug", "tags")
    prepopulated_fields = {"slug": ("title",)}
    inlines = [TestCaseInline]
    readonly_fields = ("created_at", "updated_at")

    def save_model(self, request, obj, form, change):
        if not obj.created_by_id:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(TestCase)
class TestCaseAdmin(admin.ModelAdmin):
    list_display = ("problem", "order", "is_sample", "points")
    list_filter = ("is_sample", "problem")
    search_fields = ("problem__title", "problem__slug")
