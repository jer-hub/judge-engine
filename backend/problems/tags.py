"""Pure tag parsing / normalization helpers."""

from .constants import MAX_TAG_LENGTH, MAX_TAGS


def parse_tags(raw: str | None) -> tuple[str, ...]:
    if not raw:
        return ()
    seen: set[str] = set()
    out: list[str] = []
    for part in raw.split(","):
        tag = part.strip().lower()
        if not tag:
            continue
        tag = tag[:MAX_TAG_LENGTH]
        if tag in seen:
            continue
        seen.add(tag)
        out.append(tag)
        if len(out) >= MAX_TAGS:
            break
    return tuple(out)


def normalize_tags(raw: str | None) -> str:
    return ",".join(parse_tags(raw))
