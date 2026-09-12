"""Field normalisation: titles, companies, locations, URLs.

Normalisation collapses *safe* variants while preserving the original
values elsewhere (``original_title`` etc.), per the "do not over-normalise"
principle.
"""

from __future__ import annotations

import re
from urllib.parse import urlsplit, urlunsplit

from src.models import LocationItem
from src.transform.cleaners import collapse_whitespace

# --------------------------------------------------------------------------
# Titles
# --------------------------------------------------------------------------

_TITLE_ABBREV = [
    (re.compile(r"\bSr(?:\.)?(?![\w.])", re.IGNORECASE), "Senior"),
    (re.compile(r"\bJr(?:\.)?(?![\w.])", re.IGNORECASE), "Junior"),
    (re.compile(r"\bMgr(?:\.)?(?![\w.])", re.IGNORECASE), "Manager"),
    (re.compile(r"\bEng(ineering)?\b", re.IGNORECASE), "Engineer"),
]
_TITLE_STRIP_SUFFIX = re.compile(r"\s*\((US|UK|EMEA|APAC|Remote|Hybrid|Remote-Eligible)\)\s*$", re.IGNORECASE)


def normalize_title(title: str) -> str:
    """Normalise a job title.

    Example: ``"Sr. Software Engineer"`` -> ``"Senior Software Engineer"``.
    """
    t = collapse_whitespace(title or "")
    t = _TITLE_STRIP_SUFFIX.sub("", t)
    for pattern, replacement in _TITLE_ABBREV:
        t = pattern.sub(lambda m: replacement, t)
    return collapse_whitespace(t)


# --------------------------------------------------------------------------
# Companies
# --------------------------------------------------------------------------

_COMPANY_CLEAN = [
    (re.compile(r"\s+\(?US\)?$", re.IGNORECASE), ""),
    (re.compile(r"\bInc(?:\.|,)?$", re.IGNORECASE), ""),
    (re.compile(r"\bLtd(?:\.|,)?$", re.IGNORECASE), ""),
    (re.compile(r"\bLLC(?:\.|,)?$", re.IGNORECASE), ""),
    (re.compile(r"\bLimited\b$", re.IGNORECASE), ""),
    (re.compile(r",\s*$"), ""),
]


def normalize_company(company: str) -> str:
    """Normalise a company display name (trim suffix noise)."""
    name = collapse_whitespace(company or "")
    for pattern, replacement in _COMPANY_CLEAN:
        name = pattern.sub(replacement, name)
    return collapse_whitespace(name or "Unknown")


# --------------------------------------------------------------------------
# Locations
# --------------------------------------------------------------------------

_COUNTRY_BY_NAME = {
    "united states": "US", "usa": "US", "u.s.a.": "US", "us": "US",
    "canada": "CA", "united kingdom": "GB", "uk": "GB", "england": "GB",
    "ireland": "IE", "germany": "DE", "france": "FR", "netherlands": "NL",
    "india": "IN", "singapore": "SG", "japan": "JP", "australia": "AU",
    "brazil": "BR", "mexico": "MX", "israel": "IL", "poland": "PL",
    "romania": "RO", "sweden": "SE", "switzerland": "CH", "spain": "ES",
    "italy": "IT", "taiwan": "TW", "south korea": "KR", "korea": "KR",
    "china": "CN", "hong kong": "HK", "indonesia": "ID", "malaysia": "MY",
    "philippines": "PH", "thailand": "TH", "vietnam": "VN", "uganda": "UG",
    "kenya": "KE", "nigeria": "NG", "south africa": "ZA", "egypt": "EG",
    "uae": "AE", "united arab emirates": "AE", "qatar": "QA", "saudi arabia": "SA",
}


def normalize_location_key(display_name: str, country_code: str | None) -> str:
    """Build a deterministic lower-case key for a location.

    Used as a unique identity for the ``locations`` table and for
    deduplication.
    """
    parts: list[str] = []
    if country_code:
        parts.append(country_code.upper())
    if display_name:
        parts.append(display_name)
    if not parts:
        return "UNDEFINED"
    return "|".join(parts).lower()


def build_location_items(raw_locations: list[dict]) -> list[LocationItem]:
    """Construct ranked ``LocationItem`` models from raw extractor output."""
    items: list[LocationItem] = []
    for rank, raw in enumerate(raw_locations or []):
        if not raw:
            continue
        display = (raw.get("display_name") or "").strip()
        if not display:
            continue
        country = raw.get("country_code")
        if not country:
            country = _country_from_display(display)
        item = LocationItem(
            display_name=display,
            city=raw.get("city") or None,
            state=raw.get("state") or None,
            country_code=country or None,
            rank=rank,
        )
        item.normalized_key = normalize_location_key(display, item.country_code)
        items.append(item)
    return items


def _country_from_display(display: str) -> str | None:
    """Infer a country code from a display name when the source omits it."""
    tail = display.split(",")[-1].strip().lower()
    if tail in _COUNTRY_BY_NAME:
        return _COUNTRY_BY_NAME[tail]
    return None


# --------------------------------------------------------------------------
# URLs
# --------------------------------------------------------------------------

_TRACKING_QUERY = re.compile(r"^(utm_|gclid|fbclid|mc_cid|mc_eid)", re.IGNORECASE)


def normalize_url(url: str) -> str:
    """Normalise a URL: lowercase host, strip fragments and trackers."""
    if not url:
        return ""
    scheme, netloc, path, query, fragment = urlsplit(url.strip())
    qparts = [p for p in query.split("&") if p and not _TRACKING_QUERY.match(p)]
    return urlunsplit(
        (scheme.lower(), netloc.lower(), path, "&".join(qparts), "")
    )