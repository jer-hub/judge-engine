from datetime import datetime, timedelta

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
    hold_results_until_revealed = models.BooleanField(
        default=False,
        help_text="Keep the scoreboard frozen after the end until an admin reveals it.",
    )
    # Set by "Reveal final standings": the freeze ends from this moment on.
    results_revealed_at = models.DateTimeField(null=True, blank=True)
    practice_after_end = models.BooleanField(
        default=False,
        help_text="After the contest, anyone who could see it may practice its problems.",
    )
    integrity_monitoring = models.BooleanField(
        default=True,
        help_text="Log focus/paste signals and show them to admins (warn-only; never auto-penalize).",
    )
    integrity_strict = models.BooleanField(
        default=False,
        help_text="Require fullscreen and soft-block submit until a teacher unlocks the student.",
    )
    is_archived = models.BooleanField(
        default=False,
        help_text="Hidden from students; admins can still manage or permanently delete.",
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
        """Students see the standings as of freeze_at. The freeze lifts at the
        end, or, when results are held, once an admin reveals them."""
        freeze_at = self.freeze_at
        if freeze_at is None:
            return False
        now = timezone.now()
        if self.results_revealed_at is not None and now >= self.results_revealed_at:
            return False
        if now < freeze_at or now < self.start_time:
            return False
        if now <= self.end_time or self.hold_results_until_revealed:
            return True
        # Past the official end: stay frozen while anyone's time extension
        # runs, or they would see the final standings mid-contest.
        return now <= self.last_end

    @property
    def last_end(self):
        """When the last participant's window closes (end + longest extension)."""
        longest = self.participants.aggregate(m=models.Max("extra_minutes"))["m"] or 0
        return self.end_time + timedelta(minutes=longest)

    @property
    def freeze_at(self):
        if self.freeze_scoreboard_minutes_before_end > 0:
            return self.end_time - timedelta(
                minutes=self.freeze_scoreboard_minutes_before_end
            )
        # Held results without a freeze window: freeze at the end, so time
        # extensions and late verdicts stay hidden until the reveal.
        return self.end_time if self.hold_results_until_revealed else None

    def end_time_for(self, user) -> datetime:
        """The end of this contest for one user, including a time extension."""
        extra = (
            ContestParticipant.objects.filter(contest=self, user=user)
            .values_list("extra_minutes", flat=True)
            .first()
        )
        return self.end_time + timedelta(minutes=extra or 0)


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
    # Per-student time extension (accommodations, a late start): this student
    # may keep submitting this many minutes past the contest end.
    extra_minutes = models.PositiveIntegerField(default=0)
    # Strict integrity soft-block (cleared by teacher unlock; never auto-DQ).
    integrity_blocked = models.BooleanField(default=False)
    integrity_ack_count = models.PositiveIntegerField(default=0)
    integrity_focus_since_ack = models.PositiveIntegerField(default=0)
    integrity_paste_since_ack = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = (("contest", "user"),)
        ordering = ["registered_at"]

    def __str__(self) -> str:
        return f"{self.user.username} @ {self.contest.title}"


class Clarification(models.Model):
    """A student's question during a contest, or an admin announcement.

    Announcements have no author question: an admin posts the text as the
    answer, public. A student's question stays private to them and admins
    until answered with is_public, which shows it to every contestant.
    """

    contest = models.ForeignKey(
        Contest, on_delete=models.CASCADE, related_name="clarifications"
    )
    problem = models.ForeignKey(
        ContestProblem,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="clarifications",
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="clarifications_asked",
    )
    question = models.TextField(blank=True, default="")
    answer = models.TextField(blank=True, default="")
    is_public = models.BooleanField(default=False)
    answered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="clarifications_answered",
    )
    answered_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["contest", "created_at"])]

    def __str__(self) -> str:
        return f"{self.contest.title}: {(self.question or self.answer)[:40]}"

    @property
    def is_announcement(self) -> bool:
        return not self.question


class ContestIntegrityEvent(models.Model):
    """Warn-only proctoring signal from a student's browser during a contest.

    Leads for teachers to review — never used for automatic penalties.
    Clipboard contents are never stored (paste meta may include char counts only).
    """

    class EventType(models.TextChoices):
        VISIBILITY_HIDDEN = "visibility_hidden", "Tab hidden"
        VISIBILITY_VISIBLE = "visibility_visible", "Tab visible"
        WINDOW_BLUR = "window_blur", "Window blur"
        WINDOW_FOCUS = "window_focus", "Window focus"
        EDITOR_PASTE = "editor_paste", "Editor paste"
        FULLSCREEN_EXIT = "fullscreen_exit", "Fullscreen exit"
        FULLSCREEN_ENTER = "fullscreen_enter", "Fullscreen enter"
        SOFT_BLOCK_ACK = "soft_block_ack", "Teacher unlock"

    contest = models.ForeignKey(
        Contest,
        on_delete=models.CASCADE,
        related_name="integrity_events",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="contest_integrity_events",
    )
    event_type = models.CharField(max_length=32, choices=EventType.choices)
    count = models.PositiveIntegerField(default=1)
    meta = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["contest", "user", "event_type", "created_at"],
                name="contests_in_contest_8f3a1b_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.user_id} {self.event_type} x{self.count} @ {self.contest_id}"
