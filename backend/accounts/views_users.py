from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from django.db.models import Q
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

from accounts.permissions import IsAdmin

from .csv_import import MAX_CSV_CHARS, parse_roster_csv
from .models import User
from .serializers import UserSerializer


class UserImportThrottle(ScopedRateThrottle):
    scope = "user-import"


class AdminUserWriteSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

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
            "password",
            "is_active",
        )
        read_only_fields = ("id",)

    def validate_role(self, value: str) -> str:
        if value not in (User.Role.STUDENT, User.Role.ADMIN):
            raise serializers.ValidationError("Invalid role.")
        return value

    def validate(self, attrs):
        password = attrs.get("password")
        if password:
            user = self.instance or User(
                username=attrs.get("username", ""),
                email=attrs.get("email", ""),
                first_name=attrs.get("first_name", ""),
                last_name=attrs.get("last_name", ""),
            )
            try:
                validate_password(password, user=user)
            except DjangoValidationError as exc:
                raise serializers.ValidationError({"password": list(exc.messages)}) from exc
        return attrs

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance


class PasswordResetSerializer(serializers.Serializer):
    password = serializers.CharField(min_length=8)


class UserImportSerializer(serializers.Serializer):
    csv_text = serializers.CharField(
        max_length=MAX_CSV_CHARS,
        trim_whitespace=False,
        allow_blank=False,
    )
    dry_run = serializers.BooleanField(default=False, required=False)


def _format_row_errors(serializer_errors) -> str:
    """Field-name-only messages — never echo invalid passwords/values."""
    parts: list[str] = []
    if isinstance(serializer_errors, dict):
        for field, msgs in serializer_errors.items():
            if isinstance(msgs, (list, tuple)):
                text = "; ".join(str(m) for m in msgs)
            else:
                text = str(msgs)
            parts.append(f"{field}: {text}")
    else:
        parts.append(str(serializer_errors))
    return "; ".join(parts) if parts else "Invalid row."


class UserViewSet(viewsets.ModelViewSet):
    """Admin-only roster management (no public registration)."""

    permission_classes = [IsAuthenticated, IsAdmin]
    queryset = User.objects.all().order_by("username")

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return AdminUserWriteSerializer
        if self.action == "import_users":
            return UserImportSerializer
        return UserSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        role = self.request.query_params.get("role")
        if role:
            qs = qs.filter(role=role)
        search = self.request.query_params.get("search")
        if search:
            qs = qs.filter(
                Q(username__icontains=search)
                | Q(class_section__icontains=search)
                | Q(school_id__icontains=search)
            )
        return qs

    def destroy(self, request, *args, **kwargs):
        user = self.get_object()
        if user.id == request.user.id:
            return Response(
                {"detail": "You cannot delete your own account."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().destroy(request, *args, **kwargs)

    @action(detail=True, methods=["post"], url_path="reset-password")
    def reset_password(self, request, pk=None):
        user = self.get_object()
        serializer = PasswordResetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user.set_password(serializer.validated_data["password"])
        user.save(update_fields=["password"])
        return Response({"detail": "Password updated."})

    @action(
        detail=False,
        methods=["post"],
        url_path="import",
        url_name="import",
        throttle_classes=[UserImportThrottle],
    )
    def import_users(self, request):
        serializer = UserImportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        csv_text = serializer.validated_data["csv_text"]
        dry_run = serializer.validated_data.get("dry_run", False)

        try:
            parsed = parse_roster_csv(csv_text)
        except ValueError as exc:
            raise serializers.ValidationError({"csv_text": str(exc)}) from exc

        created = 0
        skipped = 0
        failed = 0
        created_usernames: list[str] = []
        errors: list[dict] = []

        for row in parsed:
            username = (row.data.get("username") or "").strip()
            if row.error:
                failed += 1
                if len(errors) < 100:
                    errors.append(
                        {"row": row.line_no, "username": username, "error": row.error}
                    )
                continue

            if User.objects.filter(username__iexact=username).exists():
                skipped += 1
                continue

            payload = {
                **row.data,
                "role": User.Role.STUDENT,
            }
            write = AdminUserWriteSerializer(data=payload)
            if not write.is_valid():
                failed += 1
                if len(errors) < 100:
                    errors.append(
                        {
                            "row": row.line_no,
                            "username": username,
                            "error": _format_row_errors(write.errors),
                        }
                    )
                continue

            if dry_run:
                created += 1
                created_usernames.append(username)
                continue

            try:
                with transaction.atomic():
                    # Re-check inside the savepoint to avoid TOCTOU miscounts
                    if User.objects.filter(username__iexact=username).exists():
                        skipped += 1
                        continue
                    user = write.save()
            except IntegrityError:
                skipped += 1
                continue
            except Exception:
                failed += 1
                if len(errors) < 100:
                    errors.append(
                        {
                            "row": row.line_no,
                            "username": username,
                            "error": "Could not create user.",
                        }
                    )
                continue

            created += 1
            created_usernames.append(user.username)

        return Response(
            {
                "created": created,
                "skipped": skipped,
                "failed": failed,
                "dry_run": dry_run,
                "created_usernames": created_usernames,
                "errors": errors,
            }
        )
