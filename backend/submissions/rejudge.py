"""Reset submissions to Pending and queue them for judging again."""
from __future__ import annotations

import logging

from django.db import transaction
from django.db.models import QuerySet
from django.utils import timezone

from .models import Submission, SubmissionResult

logger = logging.getLogger("judge")

IN_FLIGHT = (Submission.Status.PENDING, Submission.Status.JUDGING)
# Above this many, broker calls happen in a Celery task: one per submission
# inside the web request could run past gunicorn's timeout for a big contest.
INLINE_ENQUEUE_MAX = 50


def queue_rejudge(submissions: QuerySet, include_in_flight: bool = False) -> list[int]:
    """Re-judge the given submissions; returns the ids queued.

    Submissions already Pending/Judging are skipped unless include_in_flight
    (a force rejudge, e.g. one stuck after a worker crash). Dropping the
    claim makes any task still judging the old run discard its verdict.
    """
    from judge.tasks import enqueue_judging, enqueue_judging_many

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
            # Counts as queued now, so the sweep does not treat a large batch
            # still being enqueued as lost.
            enqueued_at=timezone.now(),
        )
    if len(ids) > INLINE_ENQUEUE_MAX:
        try:
            enqueue_judging_many.delay(ids)
        except Exception:
            # They stay Pending; the recovery sweep queues them once stale.
            logger.exception("Could not enqueue a rejudge of %s submissions", len(ids))
    else:
        for submission_id in ids:
            enqueue_judging(submission_id)
    return ids
