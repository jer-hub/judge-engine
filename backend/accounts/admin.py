from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    list_display = (
        "username",
        "email",
        "role",
        "school_id",
        "class_section",
        "is_staff",
        "is_active",
    )
    list_filter = ("role", "is_staff", "is_active", "class_section")
    search_fields = ("username", "email", "school_id", "first_name", "last_name")
    fieldsets = DjangoUserAdmin.fieldsets + (
        (
            "Platform",
            {"fields": ("role", "school_id", "class_section")},
        ),
    )
    add_fieldsets = DjangoUserAdmin.add_fieldsets + (
        (
            "Platform",
            {"fields": ("role", "school_id", "class_section")},
        ),
    )
