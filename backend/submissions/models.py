from django.conf import settings
from django.db import models

from contests.models import Contest
from problems.models import Problem, TestCase


class Submission(models.Model):
    class Status(models.TextChoices):
        PENDING = "Pending", "Pending"
        JUDGING = "Judging", "Judging"
        ACCEPTED = "Accepted", "Accepted"
        WRONG_ANSWER = "WrongAnswer", "Wrong Answer"
        TIME_LIMIT_EXCEEDED = "TimeLimitExceeded", "Time Limit Exceeded"
        MEMORY_LIMIT_EXCEEDED = "MemoryLimitExceeded", "Memory Limit Exceeded"
        RUNTIME_ERROR = "RuntimeError", "Runtime Error"
        OUTPUT_LIMIT_EXCEEDED = "OutputLimitExceeded", "Output Limit Exceeded"
        COMPILE_ERROR = "CompileError", "Compile Error"
        # The judge infrastructure failed, not the student's code: no penalty,
        # and the recovery sweep re-judges it automatically.
        SYSTEM_ERROR = "SystemError", "System Error"

    class Language(models.TextChoices):
        JAVA = "java", "Java"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="submissions",
    )
    problem = models.ForeignKey(
        Problem,
        on_delete=models.CASCADE,
        related_name="submissions",
    )
    contest = models.ForeignKey(
        Contest,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="submissions",
    )
    source_code = models.TextField()
    language = models.CharField(
        max_length=20,
        choices=Language.choices,
        default=Language.JAVA,
    )
    status = models.CharField(
        max_length=32,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    compile_error = models.TextField(blank=True, default="")
    submitted_at = models.DateTimeField(auto_now_add=True, db_index=True)
    judged_at = models.DateTimeField(null=True, blank=True)
    # Set when a task claims the submission; only the task holding the current
    # claim may write results, so a stale or duplicate task cannot overwrite.
    judge_claim = models.UUIDField(null=True, blank=True, editable=False)
    judging_started_at = models.DateTimeField(null=True, blank=True, editable=False)
    # Last hand-off to the queue; the sweep re-queues Pending ones gone stale.
    enqueued_at = models.DateTimeField(null=True, blank=True, editable=False)
    # Automatic re-judges after SystemError; capped so a broken problem cannot
    # loop forever. Reset by a manual rejudge.
    auto_rejudges = models.PositiveSmallIntegerField(default=0, editable=False)

    class Meta:
        ordering = ["-submitted_at"]

    def __str__(self) -> str:
        return f"#{self.pk} {self.user} {self.problem.slug} {self.status}"


class SubmissionResult(models.Model):
    submission = models.ForeignKey(
        Submission,
        on_delete=models.CASCADE,
        related_name="results",
    )
    test_case = models.ForeignKey(
        TestCase,
        on_delete=models.CASCADE,
        related_name="results",
    )
    verdict = models.CharField(max_length=32, choices=Submission.Status.choices)
    execution_time_ms = models.PositiveIntegerField(null=True, blank=True)
    memory_used_kb = models.PositiveIntegerField(null=True, blank=True)
    stdout_snippet = models.TextField(blank=True, default="")
    stderr_snippet = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["test_case__order", "id"]
        unique_together = (("submission", "test_case"),)

    def __str__(self) -> str:
        return f"Submission {self.submission_id} TC{self.test_case_id}: {self.verdict}"
