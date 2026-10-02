from django.contrib import admin

from .models import AuditEvent


@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
    list_display = ("created_at", "actor_username", "action", "target", "status_code")
    list_filter = ("action",)
    search_fields = ("actor_username", "action", "target")
    readonly_fields = [f.name for f in AuditEvent._meta.fields] + ["fields"]

    # An audit trail is append-only.
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
