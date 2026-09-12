"""Deterministic duplicate detection.

A job's identity is a stable fingerprint over stable fields — hardcoded from
the source, job URL, normalized title, company and locations. Timestamps and
scraping metadata are deliberately excluded so re-scraping never creates a
new identity.
"""

from __future__ import annotations

import hashlib
import json

from src.models import JobRecord


def compute_dedupe_key(
    source: str,
    job_url: str,
    title: str,
    company: str,
    location_keys: list[str] | None = None,
    external_job_id: str | None = None,
) -> str:
    """Compute the deterministic identity fingerprint for a job."""
    payload = {
        "source": source,
        "external_job_id": external_job_id,
        "job_url": job_url,
        "title": title,
        "company": company,
        "locations": sorted(location_keys or []),
    }
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def dedupe_key_for_job(job: JobRecord) -> str:
    """Compute the dedupe key for a transformed job record."""
    return compute_dedupe_key(
        source=job.source,
        job_url=job.job_url,
        title=job.title,
        company=job.company_normalized,
        location_keys=[loc.normalized_key for loc in job.locations],
        external_job_id=job.external_job_id,
    )


def deduplicate(records: list[JobRecord]) -> tuple[list[JobRecord], int]:
    """De-duplicate a list in memory (first occurrence wins).

    Returns ``(unique_records, dropped_count)``.
    """
    seen: set[str] = set()
    unique: list[JobRecord] = []
    for record in records:
        key = record.dedupe_key
        if key in seen:
            continue
        seen.add(key)
        unique.append(record)
    return unique, len(records) - len(unique)