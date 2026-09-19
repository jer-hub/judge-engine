from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone

from problems.models import Problem


class Contest(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, default="")
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    is_public = models.BooleanField(default=True)
    freeze_scoreboard_minutes_before_end = models.PositiveIntegerField(
        default=0,
        help_text="Hide new solves in scoreboard this many minutes before end.",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="contests_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-start_time"]

    def __str__(self) -> str:
        return self.title

    @property
    def status(self) -> str:
        now = timezone.now()
        if now < self.start_time:
            return "upcoming"
        if now > self.end_time:
            return "past"
        return "active"

    @property
    def is_frozen(self) -> bool:
        if self.freeze_scoreboard_minutes_before_end <= 0:
            return False
        freeze_at = self.end_time - timedelta(
            minutes=self.freeze_scoreboard_minutes_before_end
        )
        now = timezone.now()
        return self.start_time <= now <= self.end_time and now >= freeze_at

    @property
    def freeze_at(self):
        if self.freeze_scoreboard_minutes_before_end <= 0:
            return None
        return self.end_time - timedelta(
            minutes=self.freeze_scoreboard_minutes_before_end
        )


class ContestProblem(models.Model):
    contest = models.ForeignKey(
        Contest,
        on_delete=models.CASCADE,
        related_name="contest_problems",
    )
    problem = models.ForeignKey(
        Problem,
        on_delete=models.CASCADE,
        related_name="contest_appearances",
    )
    letter = models.CharField(max_length=4, default="A")
    display_order = models.PositiveIntegerField(default=0)
    points = models.PositiveIntegerField(
        default=100,
        help_text="Per-contest points override (ICPC usually treats as binary).",
    )

    class Meta:
        ordering = ["display_order", "letter"]
        unique_together = (("contest", "problem"), ("contest", "letter"))

    def __str__(self) -> str:
        return f"{self.contest.title} — {self.letter}. {self.problem.title}"


class ContestParticipant(models.Model):
    contest = models.ForeignKey(
        Contest,
        on_delete=models.CASCADE,
        related_name="participants",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="contest_participations",
    )
    registered_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = (("contest", "user"),)
        ordering = ["registered_at"]

    def __str__(self) -> str:
        return f"{self.user.username} @ {self.contest.title}"
