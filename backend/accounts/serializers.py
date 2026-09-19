from rest_framework import serializers

from .models import User


class UserSerializer(serializers.ModelSerializer):
    is_platform_admin = serializers.BooleanField(read_only=True)

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "role",
            "school_id",
            "class_section",
            "is_active",
            "is_platform_admin",
            "date_joined",
        )
        read_only_fields = fields
