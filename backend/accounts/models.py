from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        STUDENT = "student", "Student"
        ADMIN = "admin", "Admin"

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.STUDENT,
    )
    school_id = models.CharField(max_length=64, blank=True, default="")
    class_section = models.CharField(max_length=64, blank=True, default="")

    @property
    def is_platform_admin(self) -> bool:
        """API/teacher privilege: role=admin or superuser (not bare is_staff)."""
        return self.role == self.Role.ADMIN or self.is_superuser

    def save(self, *args, **kwargs):
        # Django admin access follows the role: a teacher demoted to student
        # must not keep /admin/ (or any model permissions granted there).
        self.is_staff = self.role == self.Role.ADMIN or self.is_superuser
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.username} ({self.role})"
