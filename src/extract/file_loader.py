"""File-based ingestion: JSON and CSV sources.

This keeps the analytics platform functional when live extraction is
unavailable or inappropriate, per source-access policy.
"""

from __future__ import annotations

import csv
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from src.extract.base import ExtractionResult

logger = logging.getLogger(__name__)

_CSV_COLUMN_ALIASES = {
    "external_job_id": ["external_job_id", "job_id", "external_id", "id"],
    "title": ["title", "job_title"],
    "company": ["company", "company_name", "employer"],
    "location": ["location", "city", "location_name"],
    "description": ["description", "job_description", "description_text"],
    "description_html": ["description_html", "html_description"],
    "job_url": ["job_url", "url", "link", "job_link"],
    "apply_url": ["apply_url", "apply_link"],
    "posted_at": ["posted_at", "posted_date", "date_posted", "publication_date"],
    "source": ["source", "source_name"],
}


def _normalise_column(name: str) -> str:
    wanted = name.strip().lower().replace(" ", "_").replace("-", "_")
    for canonical, aliases in _CSV_COLUMN_ALIASES.items():
        if wanted in aliases:
            return canonical
    return wanted


def _parse_datetime(value: str | None) -> datetime | None:
    if not value or not str(value).strip():
        return None
    raw = str(value).strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%d/%m/%Y"):
        for candidate in (raw, raw.split(".")[0]):
            try:
                return datetime.strptime(candidate, fmt)
            except ValueError:
                continue
    try:
        return datetime.fromisoformat(raw)
    except ValueError:
        return None


def _csv_row_to_raw(row: dict, default_source: str) -> dict:
    location_value = (row.get("location") or "").strip()
    country = None
    if location_value:
        country = location_value.rsplit(",", 1)[-1].strip().upper()
        if len(country) != 2:
            country = None
    return {
        "source": (row.get("source") or default_source).strip() or default_source,
        "external_job_id": row.get("external_job_id") or None,
        "title": row.get("title") or None,
        "company": row.get("company") or None,
        "locations": (
            [{"display_name": location_value, "country_code": country}] if location_value else []
        ),
        "description": row.get("description") or None,
        "description_html": row.get("description_html") or None,
        "job_url": row.get("job_url") or None,
        "apply_url": row.get("apply_url") or None,
        "posted_at": _parse_datetime(row.get("posted_at")),
        "scraped_at": datetime.now(timezone.utc),
    }


def extract_from_json(path: str | Path, query: str | None = None) -> ExtractionResult:
    """Load raw records from a JSON file (a list of records or a map)."""
    path = Path(path)
    with path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    if isinstance(data, dict):
        records = data.get("records", data.get("jobs", []))
        if isinstance(records, dict):
            records = list(records.values())
    elif isinstance(data, list):
        records = data
    else:
        records = []

    result = ExtractionResult(source="file", query=query or path.stem)
    for record in records:
        if not isinstance(record, dict):
            logger.warning("Skipping non-dict record in %s", path)
            continue
        if "source" not in record:
            record["source"] = "file"
        if "scraped_at" not in record or not record.get("scraped_at"):
            record["scraped_at"] = datetime.now(timezone.utc)
        result.records.append(record)
    logger.info("Loaded %d raw records from %s", len(result.records), path)
    return result


def extract_from_csv(path: str | Path, query: str | None = None) -> ExtractionResult:
    """Load raw records from a flat CSV file with flexible column names."""
    path = Path(path)
    result = ExtractionResult(source="file", query=query or path.stem)
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        if reader.fieldnames is None:
            return result
        column_map = {name: _normalise_column(name) for name in reader.fieldnames}
        default_source = None
        rows: list[dict] = []
        for row in reader:
            normalised = {}
            for original, value in row.items():
                normalised[column_map.get(original, original)] = (value or "").strip()
            source_value = normalised.get("source") or ""
            if source_value:
                default_source = source_value
            rows.append(normalised)
        default_source = default_source or path.stem
        for row in rows:
            result.records.append(_csv_row_to_raw(row, default_source))
    logger.info("Loaded %d raw records from %s", len(result.records), path)
    return result