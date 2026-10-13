"""Every submitted solution in a contest or problem, as one ZIP for teachers.

Layout:
    index.csv                                   one row per submission
    <username>/<problem>/<time>_#<id>_<verdict>.java

The .java files hold the code exactly as submitted; who, what and when live
in the path and in index.csv.
"""
from __future__ import annotations

import csv
import io
import re
import zipfile

from django.utils import timezone

from contests.export import _cell

# A class's worth of contests fits easily; past this, narrow the export.
MAX_EXPORT_SUBMISSIONS = 20_000

_UNSAFE = re.compile(r"[^A-Za-z0-9._@+-]+")


def _part(text: str) -> str:
    """One safe path segment (usernames and slugs already are, mostly)."""
    return _UNSAFE.sub("_", text).strip("._") or "_"


def solutions_zip(submissions, letters: dict[int, str] | None = None) -> bytes:
    """ZIP of the given submissions. ``letters`` maps problem id to its contest
    letter, so files sort the way the contest lists its problems."""
    letters = letters or {}
    rows = (
        submissions.select_related("user", "problem", "contest")
        .order_by("user__username", "problem__slug", "submitted_at", "id")
    )
    index = io.StringIO()
    writer = csv.writer(index)
    writer.writerow([
        "submission_id", "username", "first_name", "last_name", "class_section",
        "problem", "letter", "contest", "submitted_at", "status", "file",
    ])
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for sub in rows.iterator(chunk_size=500):
            letter = letters.get(sub.problem_id, "")
            problem_dir = _part(f"{letter}-{sub.problem.slug}" if letter else sub.problem.slug)
            stamp = timezone.localtime(sub.submitted_at)
            path = (
                f"{_part(sub.user.username)}/{problem_dir}/"
                f"{stamp:%Y%m%d-%H%M%S}_#{sub.id}_{_part(sub.status)}.java"
            )
            zf.writestr(path, sub.source_code)
            writer.writerow([
                sub.id, _cell(sub.user.username), _cell(sub.user.first_name),
                _cell(sub.user.last_name), _cell(sub.user.class_section),
                _cell(sub.problem.title), letter, _cell(sub.contest.title if sub.contest else ""),
                stamp.isoformat(timespec="seconds"), sub.status, path,
            ])
        # UTF-8 with BOM so Excel shows accented names correctly.
        zf.writestr("index.csv", "﻿" + index.getvalue())
    return buffer.getvalue()
