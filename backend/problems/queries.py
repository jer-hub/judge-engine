from django.db.models import Q


def search_q(term: str) -> Q:
    """Match title, slug, or tags substring (case-insensitive)."""
    term = (term or "").strip()
    if not term:
        return Q()
    return (
        Q(title__icontains=term)
        | Q(slug__icontains=term)
        | Q(tags__icontains=term)
    )


def tag_q(tag: str) -> Q:
    """Exact tag membership in a comma-separated tags field."""
    tag = (tag or "").strip().lower()
    if not tag:
        return Q()
    return (
        Q(tags__iexact=tag)
        | Q(tags__istartswith=f"{tag},")
        | Q(tags__iendswith=f",{tag}")
        | Q(tags__icontains=f",{tag},")
    )


def multi_tag_q(raw: str) -> Q:
    """AND together exact membership for comma-separated tags."""
    parts = [p.strip() for p in (raw or "").split(",") if p.strip()]
    if not parts:
        return Q()
    combined = Q()
    for part in parts:
        combined &= tag_q(part)
    return combined
