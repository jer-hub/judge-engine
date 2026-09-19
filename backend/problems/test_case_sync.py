"""Reconcile nested test cases without wipe-deleting history.

Updating by id preserves TestCase PKs so SubmissionResult CASCADE rows
are not destroyed when an admin edits a single case.
"""

from __future__ import annotations

from dataclasses import dataclass

from rest_framework.exceptions import ValidationError

from .models import Problem, TestCase


@dataclass(frozen=True)
class SyncSummary:
    created: int
    updated: int
    deleted: int


def reconcile_test_cases(problem: Problem, incoming: list[dict]) -> SyncSummary:
    existing = {tc.id: tc for tc in problem.test_cases.all()}
    seen_ids: set[int] = set()
    created = 0
    updated = 0

    for item in incoming:
        payload = {
            "order": item.get("order", 0),
            "input_data": item["input_data"],
            "expected_output": item["expected_output"],
            "is_sample": item.get("is_sample", False),
            "points": item.get("points", 1),
        }
        tc_id = item.get("id")
        if tc_id is None:
            TestCase.objects.create(problem=problem, **payload)
            created += 1
            continue

        tc = existing.get(tc_id)
        if tc is None:
            raise ValidationError(
                {"test_cases": f"Test case id {tc_id} does not belong to this problem."}
            )
        for attr, value in payload.items():
            setattr(tc, attr, value)
        tc.save()
        seen_ids.add(tc_id)
        updated += 1

    to_delete = [tc for tc_id, tc in existing.items() if tc_id not in seen_ids]
    deleted = len(to_delete)
    if to_delete:
        TestCase.objects.filter(id__in=[tc.id for tc in to_delete]).delete()

    return SyncSummary(created=created, updated=updated, deleted=deleted)
