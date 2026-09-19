"""Parse admin roster CSV text into validated row dicts (no DB)."""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass

MAX_ROWS = 500
MAX_CSV_CHARS = 100_000

REQUIRED_HEADERS = ("username", "password")
OPTIONAL_HEADERS = (
    "first_name",
    "last_name",
    "email",
    "school_id",
    "class_section",
)
ALLOWED_HEADERS = set(REQUIRED_HEADERS) | set(OPTIONAL_HEADERS)


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

    # utf-8-sig strips BOM when present
    stream = io.StringIO(text.lstrip("\ufeff"))
    reader = csv.reader(stream)
    try:
        header_row = next(reader)
    except StopIteration as exc:
        raise ValueError("CSV is empty.") from exc

    headers = [h.strip().lower() for h in header_row]
    if not any(headers):
        raise ValueError("CSV header row is missing.")

    missing = [h for h in REQUIRED_HEADERS if h not in headers]
    if missing:
        raise ValueError(f"Missing required column(s): {', '.join(missing)}.")

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

        username = data.get("username", "")
        error: str | None = None
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
