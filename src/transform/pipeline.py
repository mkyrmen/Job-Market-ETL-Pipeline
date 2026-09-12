"""The transformation stage: raw record -> validated ``JobRecord``."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from src.models import JobRecord, LocationItem, RawRecord, SkillItem
from src.transform.classifiers import (
    classify_employment_type,
    classify_remote_type,
    classify_seniority,
)
from src.transform.cleaners import clean_description
from src.transform.dedupe import dedupe_key_for_job
from src.transform.normalizers import (
    build_location_items,
    normalize_company,
    normalize_location_key,
    normalize_title,
    normalize_url,
)
from src.transform.salary import extract_salary
from src.transform.skill_extractor import extract_skills

logger = logging.getLogger("jmip.transform")


def _locs_to_location_text(locations: list[LocationItem]) -> str:
    return " ".join(loc.display_name for loc in locations)


def transform_record(raw: RawRecord) -> JobRecord:
    """Transform one validated raw record into a normalised job record."""
    title = (raw.title or "").strip()
    original_title = title

    if not raw.job_url:
        # URL-less records (e.g. legacy import) still need a stable fingerprint
        # identity; the sign-in/apply URL is used as a fallback target.
        job_url = raw.apply_url or f"{raw.source}://{raw.external_job_id or 'anonymous'}"
    else:
        job_url = normalize_url(raw.job_url)
    apply_url = normalize_url(raw.apply_url) if raw.apply_url else None

    company = (raw.company or "").strip() or "Unknown"
    companies_normalized = normalize_company(f"{company}")

    locations = build_location_items(raw.locations)

    description = clean_description(
        [
            raw.overview_html,
            raw.description_html,
            raw.qualifications_html,
            raw.additional_qualifications_html,
            raw.description,
        ]
    )

    seniority = classify_seniority(title, description)
    remote_type = classify_remote_type(title, description, _locs_to_location_text(locations))
    employment_type = classify_employment_type(title, description)

    salary = extract_salary(description)

    skills = extract_skills(description, title=title)

    record = JobRecord(
        source=raw.source,
        external_job_id=raw.external_job_id or None,
        title=normalize_title(title),
        original_title=original_title,
        company=company,
        company_normalized=companies_normalized,
        company_external_id=raw.company_external_id or None,
        locations=locations,
        description=description,
        employment_type=employment_type,
        seniority=seniority,
        remote_type=remote_type,
        job_url=job_url,
        apply_url=apply_url,
        posted_at=raw.posted_at,
        scraped_at=raw.scraped_at or datetime.now(timezone.utc),
        salary_min=salary.low,
        salary_max=salary.high,
        salary_currency=salary.currency,
        skills=skills,
        raw_payload=raw.payload,
    )
    record.dedupe_key = dedupe_key_for_job(record)
    return record


def transform_all(raw_records: list[RawRecord]) -> list[JobRecord]:
    """Transform a batch of raw records, logging any failures."""
    transformed: list[JobRecord] = []
    failures = 0
    for raw in raw_records:
        try:
            transformed.append(transform_record(raw))
        except Exception:  # noqa: BLE001 - record-level isolation
            failures += 1
            logger.exception("Transformation failed for raw record from %s (id=%s)",
                             raw.source, raw.external_job_id)
    logger.info("Transformed %d records (%d failures)", len(transformed), failures)
    return transformed


def location_key(display: str, country_code: str | None) -> str:
    """Public helper built on the normalizer."""
    return normalize_location_key(display, country_code)