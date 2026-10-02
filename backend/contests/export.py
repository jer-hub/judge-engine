"""Contest standings as CSV, for grading in a spreadsheet."""
from __future__ import annotations

import csv
import io

from django.contrib.auth import get_user_model

from .models import Contest
from .scoreboard import build_scoreboard

# A cell starting with one of these is run as a formula by Excel/Sheets
# (CSV injection); usernames and names are typed by people, so escape them.
_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def _cell(value) -> str:
    text = "" if value is None else str(value)
    return "'" + text if text.startswith(_FORMULA_PREFIXES) else text


def standings_csv(contest: Contest, viewer, section: str | None = None) -> str:
    """Final (unfrozen, for an admin viewer) standings, one row per participant.

    ``section`` keeps only students whose class section matches (case-
    insensitive); ranks stay the contest-wide ones.
    """
    board = build_scoreboard(contest, viewer=viewer)
    usernames = [row["username"] for row in board["standings"]]
    users = {
        u.username: u for u in get_user_model().objects.filter(username__in=usernames)
    }

    out = io.StringIO()
    # BOM: Excel otherwise opens UTF-8 as ANSI and garbles names like "Peña".
    out.write("﻿")
    writer = csv.writer(out)
    header = ["Rank", "Username", "First name", "Last name", "School ID", "Section", "Solved", "Penalty"]
    for problem in board["problems"]:
        header += [f"{problem['letter']} solved at (min)", f"{problem['letter']} attempts"]
    writer.writerow(header)

    wanted = section.strip().lower() if section else None
    for row in board["standings"]:
        user = users.get(row["username"])
        user_section = user.class_section if user else ""
        if wanted is not None and user_section.strip().lower() != wanted:
            continue
        line = [
            row["rank"],
            _cell(row["username"]),
            _cell(user.first_name if user else ""),
            _cell(user.last_name if user else ""),
            _cell(user.school_id if user else ""),
            _cell(user_section),
            row["solved"],
            row["penalty"],
        ]
        for cell in row["problems"]:
            line += [cell["solve_time_min"] if cell["solved"] else "", cell["attempts"]]
        writer.writerow(line)
    return out.getvalue()
