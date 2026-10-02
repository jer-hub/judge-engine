"""Reset submissions to Pending and queue them for judging again."""
from __future__ import annotations

from django.db import transaction
from django.db.models import QuerySet

from .models import Submission, SubmissionResult

IN_FLIGHT = (Submission.Status.PENDING, Submission.Status.JUDGING)


def queue_rejudge(submissions: QuerySet, include_in_flight: bool = False) -> list[int]:
    """Re-judge the given submissions; returns the ids queued.

    Submissions already Pending/Judging are skipped unless include_in_flight
    (a force rejudge, e.g. one stuck after a worker crash). Dropping the
    claim makes any task still judging the old run discard its verdict.
    """
    from judge.tasks import enqueue_judging

    targets = Submission.objects.filter(pk__in=submissions.values("pk"))
    if not include_in_flight:
        targets = targets.exclude(status__in=IN_FLIGHT)
    with transaction.atomic():
        ids = list(targets.select_for_update().values_list("pk", flat=True))
        SubmissionResult.objects.filter(submission_id__in=ids).delete()
        Submission.objects.filter(pk__in=ids).update(
            status=Submission.Status.PENDING,
            compile_error="",
            judged_at=None,
            judge_claim=None,
            judging_started_at=None,
            auto_rejudges=0,
        )
    for submission_id in ids:
        enqueue_judging(submission_id)
    return ids
