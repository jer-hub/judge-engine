"""Celery tasks for account management."""
from __future__ import annotations

from celery import shared_task


@shared_task
def import_users_task(csv_text: str) -> dict:
    """Bulk student import; the summary never contains passwords.

    The CSV (with passwords) sits in the Redis broker only until a worker
    takes the task; results store just the summary (result_extended is off).
    """
    from .csv_import import parse_roster_csv
    from .views_users import run_import

    return run_import(parse_roster_csv(csv_text), dry_run=False)
