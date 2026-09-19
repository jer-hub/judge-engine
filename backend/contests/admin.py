from django.contrib import admin

from .models import Contest, ContestParticipant, ContestProblem


class ContestProblemInline(admin.TabularInline):
    model = ContestProblem
    extra = 1
    autocomplete_fields = ("problem",)


class ContestParticipantInline(admin.TabularInline):
    model = ContestParticipant
    extra = 0
    autocomplete_fields = ("user",)
    readonly_fields = ("registered_at",)


@admin.register(Contest)
class ContestAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "start_time",
        "end_time",
        "is_public",
        "freeze_scoreboard_minutes_before_end",
    )
    list_filter = ("is_public",)
    search_fields = ("title",)
    inlines = [ContestProblemInline, ContestParticipantInline]

    def save_model(self, request, obj, form, change):
        if not obj.created_by_id:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(ContestProblem)
class ContestProblemAdmin(admin.ModelAdmin):
    list_display = ("contest", "letter", "problem", "points", "display_order")
    list_filter = ("contest",)
    autocomplete_fields = ("contest", "problem")


@admin.register(ContestParticipant)
class ContestParticipantAdmin(admin.ModelAdmin):
    list_display = ("contest", "user", "registered_at")
    list_filter = ("contest",)
    autocomplete_fields = ("contest", "user")
    search_fields = ("user__username", "contest__title")
