"""Celery tasks for account management."""
from __future__ import annotations

from celery import shared_task


@shared_task
def import_users_task(csv_text: str, actor_id: int | None = None) -> dict:
    """Bulk student import; the summary never contains passwords.

    The CSV (with passwords) sits in the Redis broker only until a worker
    takes the task; results store just the summary (result_extended is off).
    """
    from audit.models import AuditEvent

    from .csv_import import parse_roster_csv
    from .models import User
    from .views_users import run_import

    summary = run_import(parse_roster_csv(csv_text), dry_run=False)
    # The request only logged that an import was queued; record what it did.
    actor = User.objects.filter(pk=actor_id).first() if actor_id else None
    AuditEvent.objects.create(
        actor=actor,
        actor_username=actor.username if actor else "",
        action="user.import_users.done",
        target=(
            f"created {summary.get('created', 0)}, skipped {summary.get('skipped', 0)}, "
            f"failed {summary.get('failed', 0)}"
        ),
        status_code=200,
    )
    return summary
