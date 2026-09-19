from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.text import slugify

from .constants import (
    MAX_MEMORY_LIMIT_MB,
    MAX_TEST_CASE_POINTS,
    MAX_TIME_LIMIT_MS,
    MIN_MEMORY_LIMIT_MB,
    MIN_TIME_LIMIT_MS,
)
from .tags import normalize_tags


class Problem(models.Model):
    class Difficulty(models.TextChoices):
        EASY = "easy", "Easy"
        MEDIUM = "medium", "Medium"
        HARD = "hard", "Hard"

    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    statement = models.TextField(help_text="Markdown statement shown to students")
    time_limit_ms = models.PositiveIntegerField(
        default=settings.JUDGE_DEFAULT_TIME_LIMIT_MS,
        validators=[
            MinValueValidator(MIN_TIME_LIMIT_MS),
            MaxValueValidator(MAX_TIME_LIMIT_MS),
        ],
    )
    memory_limit_mb = models.PositiveIntegerField(
        default=settings.JUDGE_DEFAULT_MEMORY_LIMIT_MB,
        validators=[
            MinValueValidator(MIN_MEMORY_LIMIT_MB),
            MaxValueValidator(MAX_MEMORY_LIMIT_MB),
        ],
    )
    difficulty = models.CharField(
        max_length=20,
        choices=Difficulty.choices,
        default=Difficulty.EASY,
    )
    tags = models.CharField(max_length=255, blank=True, default="")
    is_published = models.BooleanField(default=False)
    run_all_tests = models.BooleanField(
        default=False,
        help_text=(
            "If true, run all tests for full per-test feedback; else stop at first failure. "
            "Scoreboard remains ICPC binary (solved/not)."
        ),
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="problems_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["title"]

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.title) or "problem"
            slug = base
            n = 1
            while Problem.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                n += 1
                slug = f"{base}-{n}"
            self.slug = slug
        self.tags = normalize_tags(self.tags)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.title

    @property
    def tag_list(self) -> list[str]:
        if not self.tags:
            return []
        return [t.strip() for t in self.tags.split(",") if t.strip()]


class TestCase(models.Model):
    problem = models.ForeignKey(
        Problem,
        on_delete=models.CASCADE,
        related_name="test_cases",
    )
    input_data = models.TextField()
    expected_output = models.TextField()
    is_sample = models.BooleanField(
        default=False,
        help_text="Sample cases are visible to students; others are hidden.",
    )
    points = models.PositiveIntegerField(
        default=1,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(MAX_TEST_CASE_POINTS),
        ],
    )
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self) -> str:
        kind = "sample" if self.is_sample else "hidden"
        return f"{self.problem.slug} #{self.order} ({kind})"
