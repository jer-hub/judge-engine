"""Parse admin roster CSV text into validated row dicts (no DB)."""

from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass

MAX_ROWS = 500
MAX_CSV_CHARS = 100_000

FIELDS = (
    "username",
    "password",
    "first_name",
    "last_name",
    "email",
    "school_id",
    "class_section",
)
ALLOWED_HEADERS = set(FIELDS)

# Other spellings of the fields, after _normalize_header(). A Google Forms
# export names its columns after the questions ("First name", "Email
# Address", "School ID"), so its CSV imports without renaming anything.
# Columns that match nothing (e.g. "Timestamp") are ignored.
HEADER_ALIASES = {
    "user_name": "username",
    "login": "username",
    "first": "first_name",
    "firstname": "first_name",
    "given_name": "first_name",
    "last": "last_name",
    "lastname": "last_name",
    "surname": "last_name",
    "family_name": "last_name",
    "email_address": "email",
    "e_mail": "email",
    "e_mail_address": "email",
    "student_id": "school_id",
    "student_number": "school_id",
    "student_no": "school_id",
    "id_number": "school_id",
    "school_id_number": "school_id",
    "section": "class_section",
    "class": "class_section",
    "course_and_section": "class_section",
    "year_and_section": "class_section",
    "course_year_and_section": "class_section",
}


def _normalize_header(name: str) -> str:
    """'First name' -> 'first_name', 'E-mail Address' -> 'e_mail_address'."""
    key = re.sub(r"[^a-z0-9]+", "_", (name or "").strip().lower()).strip("_")
    return HEADER_ALIASES.get(key, key)


@dataclass(frozen=True)
class ParsedRow:
    line_no: int
    data: dict[str, str]
    error: str | None = None


def parse_roster_csv(text: str) -> list[ParsedRow]:
    if text is None:
        raise ValueError("CSV text is required.")
    if len(text) > MAX_CSV_CHARS:
        raise ValueError(f"CSV is too large (max {MAX_CSV_CHARS} characters).")
    # PostgreSQL text cannot hold NUL, so a row with one would crash the
    # import midway. It usually means the file was saved as UTF-16.
    if "\x00" in text:
        raise ValueError("CSV contains NUL characters. Save it as CSV (UTF-8) and try again.")

    # utf-8-sig strips BOM when present
    stream = io.StringIO(text.lstrip("\ufeff"))
    reader = csv.reader(stream)
    try:
        header_row = next(reader)
    except StopIteration as exc:
        raise ValueError("CSV is empty.") from exc

    headers = [_normalize_header(h) for h in header_row]
    if not any(headers):
        raise ValueError("CSV header row is missing.")

    # The school ID doubles as the username when there is no username column.
    if "username" not in headers and "school_id" not in headers:
        raise ValueError("Missing required column: username (or school_id).")

    # Map allowed header -> first column index
    col_index: dict[str, int] = {}
    for idx, name in enumerate(headers):
        if name in ALLOWED_HEADERS and name not in col_index:
            col_index[name] = idx

    rows: list[ParsedRow] = []
    seen_usernames: set[str] = set()
    data_rows = 0

    for offset, raw in enumerate(reader):
        line_no = offset + 2  # header is line 1
        if not raw or all(not (cell or "").strip() for cell in raw):
            continue

        data_rows += 1
        if data_rows > MAX_ROWS:
            raise ValueError(f"CSV has too many rows (max {MAX_ROWS}).")

        data: dict[str, str] = {}
        for key, idx in col_index.items():
            value = raw[idx].strip() if idx < len(raw) and raw[idx] is not None else ""
            data[key] = value

        if not data.get("username"):
            data["username"] = data.get("school_id", "")
        username = data["username"]
        error: str | None = None
        if not username:
            error = "Missing username (and no school ID to use instead)."
        if username:
            key = username.casefold()
            if key in seen_usernames:
                error = "Duplicate username in this CSV."
            else:
                seen_usernames.add(key)

        rows.append(ParsedRow(line_no=line_no, data=data, error=error))

    if not rows:
        raise ValueError("CSV has no data rows.")

    return rows
