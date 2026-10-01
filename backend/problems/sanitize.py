"""Server-side cleanup of rich-text (HTML) problem statements.

The frontend already sanitizes on render (DOMPurify / rehype-sanitize); this
keeps the stored copy safe for every other consumer (Django admin, exports,
API clients). Markdown statements pass through untouched — running an HTML
sanitizer over Markdown would mangle it (``> quote`` becomes ``&gt; quote``).
"""
import re

import bleach

# What the admin RichTextEditor (Quill) produces, plus common inline markup.
ALLOWED_TAGS = frozenset(
    {
        "p", "br", "h1", "h2", "h3", "h4", "h5", "h6",
        "strong", "b", "em", "i", "u", "s", "sub", "sup",
        "ol", "ul", "li", "blockquote", "pre", "code", "span", "a",
        "table", "thead", "tbody", "tr", "th", "td", "hr",
    }
)
ALLOWED_ATTRIBUTES = {
    "a": ["href", "title", "target", "rel"],
    # Quill encodes indentation, alignment and code highlighting as classes.
    "*": ["class"],
}
ALLOWED_PROTOCOLS = frozenset({"http", "https", "mailto"})

_HTML_START = re.compile(r"^\s*<")


def looks_like_html(text: str) -> bool:
    """Same rule as the frontend's StatementContent."""
    return bool(_HTML_START.match(text or ""))


def sanitize_statement(text: str) -> str:
    if not looks_like_html(text):
        return text
    return bleach.clean(
        text,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        protocols=ALLOWED_PROTOCOLS,
        strip=True,
        strip_comments=True,
    )
