"""Google Careers extractor.

Primary method: polite HTTPS requests against the public search-results page,
then parse the server-rendered ``AF_initDataCallback`` JSON payload the page
embeds. This yields structured fields (numeric job id, title, apply URL,
HTML description/qualifications, structured location, publish timestamps)
without a browser, CAPTCHAs or any auth/anti-bot bypass.

The payload format is unofficial and may change; parser functions are
versioned here and fail loudly with an ``ExtractionError`` rather than
silently returning garbage.
"""

from __future__ import annotations

import json
import logging
import re
import time
from datetime import datetime, timezone

import requests

from src.config import get_settings
from src.extract.base import ExtractionResult

logger = logging.getLogger(__name__)

SEARCH_URL = "https://www.google.com/about/careers/applications/jobs/results/"
_JOB_URL_TEMPLATE = "https://www.google.com/about/careers/applications/jobs/results/{job_id}"

# Payload format version tolerated by this parser. Bump intentionally when
# the field layout of the embedded JSON is remapped.
_PAYLOAD_VERSION = 2

_JOB_ID_RE = re.compile(r"\d{15,25}")
_COMPANY_RESOURCE_RE = re.compile(r"companies/([0-9a-f-]{36})")

# HTML fragment fields inside a google-careers record (1-indexed per layout).
_DESC_FIELD = 3
_QUALS_FIELD = 4
_COMPANY_PATH_FIELD = 5
_COMPANY_NAME_FIELD = 7
_LOCATION_FIELD = 9
_OVERVIEW_FIELD = 10
_TIMESTAMP_FIELD_1 = 12
_TIMESTAMP_FIELD_2 = 13
_ADDITIONAL_QUALS_FIELD = 19


class ExtractionError(RuntimeError):
    """Raised when the Google Careers payload cannot be parsed."""


def _html_field(record: list, index: int) -> str | None:
    """Return the HTML string at ``record[index][1]`` if present."""
    if index >= len(record):
        return None
    value = record[index]
    if isinstance(value, list) and len(value) > 1 and isinstance(value[1], str):
        return value[1]
    return None


def _company_uuid(record: list) -> str | None:
    if _COMPANY_PATH_FIELD >= len(record):
        return None
    path = record[_COMPANY_PATH_FIELD]
    if isinstance(path, str):
        m = _COMPANY_RESOURCE_RE.search(path)
        if m:
            return m.group(1)
    return None


def _locations(record: list) -> list[dict]:
    if _LOCATION_FIELD >= len(record):
        return []
    raw = record[_LOCATION_FIELD]
    if not isinstance(raw, list):
        return []
    locations: list[dict] = []
    for group in raw:
        if not isinstance(group, list) or not group:
            continue
        display = group[0]
        if not isinstance(display, str) or not display.strip():
            continue
        locations.append(
            {
                "display_name": display.strip(),
                "city": group[2] if len(group) > 2 and isinstance(group[2], str) else None,
                "state": group[4] if len(group) > 4 and isinstance(group[4], str) else None,
                "country_code": group[5] if len(group) > 5 and isinstance(group[5], str) else None,
            }
        )
    return locations


def _posted_at(record: list) -> datetime | None:
    timestamps: list[int] = []
    for index in (_TIMESTAMP_FIELD_1, _TIMESTAMP_FIELD_2):
        if index < len(record):
            value = record[index]
            if isinstance(value, list) and value and isinstance(value[0], int):
                timestamps.append(value[0])
    if not timestamps:
        return None
    try:
        return datetime.fromtimestamp(min(timestamps), tz=None)
    except (OverflowError, OSError, ValueError):
        return None


def record_to_raw(record: list, query: str, scraped_at: datetime | None = None) -> dict | None:
    """Convert one payload record into the pipeline's raw-record schema."""
    if not isinstance(record, list) or not record:
        return None

    job_id = record[0] if isinstance(record[0], str) else None
    if not job_id or not _JOB_ID_RE.fullmatch(job_id):
        return None
    title = record[1] if isinstance(record[1], str) else None
    if not title:
        return None

    apply_url = record[2] if isinstance(record[2], str) else None
    company_name = record[_COMPANY_NAME_FIELD] if _COMPANY_NAME_FIELD < len(record) else None

    return {
        "source": "google_careers",
        "external_job_id": job_id,
        "title": title.strip(),
        "company": company_name.strip() if isinstance(company_name, str) else None,
        "company_external_id": _company_uuid(record),
        "locations": _locations(record),
        "description_html": _html_field(record, _DESC_FIELD),
        "overview_html": _html_field(record, _OVERVIEW_FIELD),
        "qualifications_html": _html_field(record, _QUALS_FIELD),
        "additional_qualifications_html": _html_field(record, _ADDITIONAL_QUALS_FIELD),
        "job_url": _JOB_URL_TEMPLATE.format(job_id=job_id),
        "apply_url": apply_url,
        "posted_at": _posted_at(record),
        "scraped_at": scraped_at or datetime.now(timezone.utc),
        "payload": {"payload_version": _PAYLOAD_VERSION, "record": record},
    }


def _find_ds1_payload(html: str) -> list:
    marker = "key: 'ds:1'"
    index = html.find(marker)
    if index < 0:
        raise ExtractionError("Google Careers payload (ds:1) not found in page")
    segment = html[index : index + 3_000_000]
    data_start = segment.find("data:[")
    if data_start < 0:
        raise ExtractionError("'data:[' not found in ds:1 callback")
    start = data_start + len("data:[")
    depth = 0
    end = None
    for idx in range(start, len(segment)):
        ch = segment[idx]
        if ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
            if depth == 0:
                end = idx + 1
                break
    if end is None:
        raise ExtractionError("Unbalanced brackets in ds:1 payload")
    raw = segment[start:end]
    raw = raw.replace("undefined", "null").replace("NaN", "null")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ExtractionError(f"Malformed ds:1 JSON near offset {exc.pos}") from exc
    if not isinstance(data, list):
        raise ExtractionError("ds:1 payload is not a JSON array")
    return data


def _locate_job_records(data: list) -> list[list]:
    """Recursively find the list of 21-field job records."""

    def walk(node):
        if not isinstance(node, list):
            return None
        if node and isinstance(node[0], list):
            first = node[0]
            if first and isinstance(first[0], str) and _JOB_ID_RE.fullmatch(first[0]):
                return node
            for item in node:
                result = walk(item)
                if result is not None:
                    return result
        return None

    records = walk(data)
    if records is None:
        raise ExtractionError("No job records found in ds:1 payload")
    return records


def parse_google_payload(html: str, query: str = "") -> list[dict]:
    """Parse a Google Careers search-results page into raw records."""
    data = _find_ds1_payload(html)
    job_records = _locate_job_records(data)
    scraped_at = datetime.now(timezone.utc)
    raw_records: list[dict] = []
    for record in job_records:
        raw = record_to_raw(record, query, scraped_at)
        if raw is not None:
            raw_records.append(raw)
    logger.debug("Parsed %d raw records from page payload", len(raw_records))
    return raw_records


class GoogleCareersExtractor:
    """Fetch and parse structured job data from Google Careers."""

    def __init__(self) -> None:
        settings = get_settings()
        self._session = requests.Session()
        self._session.headers.update(
            {
                "User-Agent": settings.user_agent,
                "Accept-Language": "en-US,en;q=0.9",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            }
        )
        self._timeout = settings.request_timeout_seconds
        self._max_retries = settings.max_http_retries

    def _fetch(self, url: str) -> str:
        last_error: Exception | None = None
        for attempt in range(1, self._max_retries + 1):
            try:
                response = self._session.get(url, timeout=self._timeout)
                response.raise_for_status()
                return response.text
            except requests.RequestException as exc:
                last_error = exc
                logger.warning(
                    "Request failed for %s (attempt %d/%d): %s",
                    url, attempt, self._max_retries, exc,
                )
                if attempt < self._max_retries:
                    time.sleep(1.5 * attempt)
        raise ExtractionError(f"Could not fetch {url}: {last_error}")

    def extract(self, query: str, limit: int | None = None) -> ExtractionResult:
        """Extract raw records for *query* across as many pages as needed."""
        result = ExtractionResult(source="google_careers", query=query)
        limit = limit or 100
        page = 1
        seen_ids: set[str] = set()

        while len(result.records) < limit:
            url = f"{SEARCH_URL}?q={query}&hl=en_US&page_number={page}"
            logger.info("Fetching Google Careers search page %d for '%s'", page, query)
            html = self._fetch(url)
            page_records = parse_google_payload(html, query=query)
            result.pages_fetched += 1

            if not page_records:
                logger.info("No further records; stopping pagination at page %d", page)
                break

            fresh = 0
            for raw in page_records:
                if raw["external_job_id"] in seen_ids:
                    continue
                seen_ids.add(raw["external_job_id"])
                result.records.append(raw)
                fresh += 1
                if len(result.records) >= limit:
                    break

            if fresh == 0:
                logger.info("No fresh records on page %d; stopping", page)
                break
            page += 1

        logger.info(
            "Extraction complete: %d records from %d page(s) for '%s'",
            len(result.records), result.pages_fetched, query,
        )
        return result