import secrets
import string

import redis
from celery.result import AsyncResult
from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.http import Http404
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

from accounts.permissions import CanModifyTargetUser, IsAdmin
from audit.mixins import AuditedViewSetMixin

from .csv_import import MAX_CSV_CHARS, parse_roster_csv
from .models import User
from .serializers import UserSerializer
from .sessions import revoke_user_sessions

# How long an import's owner record (and so its result) stays fetchable.
IMPORT_OWNER_TTL_SECONDS = 3600
# Hashing costs ~0.3 s per password; keep one request well inside gunicorn's
# 30 s timeout. A class section is usually smaller than this.
MAX_BULK_RESET = 50
# No look-alikes (0/O, 1/l/I): passwords get read off printed slips.
_LOOKALIKES = set("0Oo1lIi")
_ALPHABET = "".join(c for c in string.ascii_letters + string.digits if c not in _LOOKALIKES)


def generate_password(length: int = 10) -> str:
    return "".join(secrets.choice(_ALPHABET) for _ in range(length))


def _redis_client():
    return redis.from_url(settings.REDIS_URL, decode_responses=True)


def _import_owner_key(task_id: str) -> str:
    return f"import-owner:{task_id}"


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
        request = self.context.get("request")
        if self.instance is not None and request and self.instance.pk == request.user.pk:
            # Don't let an admin lock themselves (possibly the last admin) out.
            if "role" in attrs and attrs["role"] != User.Role.ADMIN:
                raise serializers.ValidationError(
                    {"role": "You cannot remove your own admin role."}
                )
            if attrs.get("is_active") is False:
                raise serializers.ValidationError(
                    {"is_active": "You cannot deactivate your own account."}
                )
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
        deactivating = instance.is_active and validated_data.get("is_active") is False
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        if password or deactivating:
            revoke_user_sessions(instance)
        return instance


class PasswordResetSerializer(serializers.Serializer):
    password = serializers.CharField(min_length=8)

    def validate_password(self, value: str) -> str:
        try:
            validate_password(value, user=self.context.get("user"))
        except DjangoValidationError as exc:
            raise serializers.ValidationError(list(exc.messages)) from exc
        return value


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


class UserViewSet(AuditedViewSetMixin, viewsets.ModelViewSet):
    """Admin-only roster management (no public registration)."""

    permission_classes = [IsAuthenticated, IsAdmin, CanModifyTargetUser]
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
        # Deleting cascades to submissions, which silently rewrites past
        # scoreboards and grades. Disabling keeps the history.
        count = user.submissions.count()
        if count:
            return Response(
                {
                    "detail": f"{user.username} has {count} submission{'s' if count != 1 else ''}; "
                    "disable the account instead to keep contest results intact."
                },
                status=status.HTTP_409_CONFLICT,
            )
        # End their sessions first: a refresh token for a deleted user would
        # otherwise fail the user lookup on every request.
        revoke_user_sessions(user)
        return super().destroy(request, *args, **kwargs)

    @action(detail=False, methods=["post"], url_path="bulk-reset-password")
    def bulk_reset_password(self, request):
        """Give students new random passwords: {"section": "BSIT-1A"} or
        {"usernames": [...]}. Returns the new passwords once, for the teacher
        to hand out; existing sessions are ended. Admin accounts are never
        included."""
        section = request.data.get("section")
        usernames = request.data.get("usernames")
        students = (
            User.objects.filter(role=User.Role.STUDENT, is_superuser=False)
            .exclude(pk=request.user.pk)
        )
        if isinstance(section, str) and section.strip():
            students = students.filter(class_section__iexact=section.strip())
        elif isinstance(usernames, list) and usernames and all(isinstance(u, str) for u in usernames):
            students = students.filter(username__in=[u.strip() for u in usernames])
        else:
            raise serializers.ValidationError(
                {"detail": "Give a class section or a list of usernames."}
            )
        students = list(students.order_by("username"))
        if not students:
            raise serializers.ValidationError({"detail": "No student accounts matched."})
        if len(students) > MAX_BULK_RESET:
            raise serializers.ValidationError(
                {"detail": f"{len(students)} students matched; reset at most {MAX_BULK_RESET} at a time."}
            )
        results = []
        for user in students:
            password = generate_password()
            user.set_password(password)
            user.save(update_fields=["password"])
            revoke_user_sessions(user)
            results.append(
                {
                    "username": user.username,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "class_section": user.class_section,
                    "password": password,
                }
            )
        return Response({"count": len(results), "results": results})

    @action(detail=True, methods=["post"], url_path="reset-password")
    def reset_password(self, request, pk=None):
        user = self.get_object()
        serializer = PasswordResetSerializer(data=request.data, context={"user": user})
        serializer.is_valid(raise_exception=True)
        user.set_password(serializer.validated_data["password"])
        user.save(update_fields=["password"])
        # A reset usually means the account was compromised: end its sessions.
        revoke_user_sessions(user)
        return Response({"detail": "Password updated."})

    @action(
        detail=False,
        methods=["post"],
        url_path="import",
        url_name="import",
        throttle_classes=[UserImportThrottle],
    )
    def import_users(self, request):
        """Dry runs answer inline (no hashing, fast). Real imports hash every
        password (~0.3 s each), far past gunicorn's timeout for a class-sized
        roster, so they run as a Celery task: 202 + task_id, then poll."""
        serializer = UserImportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        csv_text = serializer.validated_data["csv_text"]
        dry_run = serializer.validated_data.get("dry_run", False)

        try:
            parsed = parse_roster_csv(csv_text)
        except ValueError as exc:
            raise serializers.ValidationError({"csv_text": str(exc)}) from exc

        if dry_run:
            return Response(run_import(parsed, dry_run=True))

        from .tasks import import_users_task

        async_result = import_users_task.delay(csv_text=csv_text, actor_id=request.user.id)
        _redis_client().setex(
            _import_owner_key(async_result.id), IMPORT_OWNER_TTL_SECONDS, request.user.id
        )
        return Response(
            {"task_id": async_result.id, "status": "Pending"},
            status=status.HTTP_202_ACCEPTED,
        )

    @action(
        detail=False,
        methods=["get"],
        url_path=r"import/(?P<task_id>[\w-]+)",
        url_name="import-result",
    )
    def import_result(self, request, task_id: str):
        owner = _redis_client().get(_import_owner_key(task_id))
        if owner is None or owner != str(request.user.id):
            raise Http404

        result = AsyncResult(task_id)
        if result.state in ("PENDING", "RECEIVED"):
            return Response({"task_id": task_id, "status": "Pending"})
        if result.state in ("STARTED", "RETRY"):
            return Response({"task_id": task_id, "status": "Running"})
        if result.state != "SUCCESS":
            return Response(
                {
                    "task_id": task_id,
                    "status": "Failed",
                    "detail": "Import failed. Check which accounts exist, then retry; "
                    "existing usernames are skipped.",
                }
            )
        return Response({"task_id": task_id, "status": "Done", **(result.result or {})})


def run_import(parsed, dry_run: bool) -> dict:
    """Create student accounts from parsed CSV rows; returns the summary."""
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

    return {
        "created": created,
        "skipped": skipped,
        "failed": failed,
        "dry_run": dry_run,
        "created_usernames": created_usernames,
        "errors": errors,
    }