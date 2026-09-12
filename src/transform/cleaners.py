"""Text cleaning helpers for the transform layer."""

from __future__ import annotations

import re

from bs4 import BeautifulSoup

# Recompose posts/numbers/lists split across lines ("Jr. Engineer", "$12,000").
_BOUNDARY_JOIN = re.compile(r"(?<=[A-Za-z0-9.,%$])\s*\n\s*(?=[a-z0-9$])")
_WHITESPACE = re.compile(r"\s+")

# Common page chrome / boilerplate that leaks into body-text extraction.
_BOILERPLATE = re.compile(
    r"^\s*(roles open for this team|home|Careers|jobs matched|skip navigation links)\s*$",
    re.IGNORECASE | re.MULTILINE,
)


def html_to_text(html: str | None) -> str:
    """Convert an HTML fragment to readable plain text."""
    if not html:
        return ""
    soup = BeautifulSoup(html, "html.parser")
    for tag in ("script", "style", "noscript"):
        for node in soup.find_all(tag):
            node.decompose()
    text = soup.get_text(" ")
    return collapse_whitespace(text)


def collapse_whitespace(text: str) -> str:
    """Normalise all whitespace runs to single spaces."""
    text = _BOUNDARY_JOIN.sub(" ", text or "")
    text = _WHITESPACE.sub(" ", text)
    return text.strip()


def remove_boilerplate(text: str) -> str:
    """Drop known page-chrome lines from extracted descriptions."""
    return _BOILERPLATE.sub("", text or "").strip()


def clean_description(parts: list[str | None]) -> str:
    """Merge, clean and normalise description HTML fragments."""
    texts = [html_to_text(part) for part in parts if part]
    merged = " ".join(t for t in texts if t)
    merged = collapse_whitespace(remove_boilerplate(merged))
    return merged


def slugify(text: str, max_len: int = 64) -> str:
    """Lower-case, hyphenated identifier derived from *text*."""
    slug = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return slug[:max_len]