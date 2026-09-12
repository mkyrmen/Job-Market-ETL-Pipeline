"""Pydantic models for validated, normalised job records.

A single ``JobRecord`` (transformed) is the contract between the transform
layer and the load layer. The database schema is a relational projection of
these models.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field, field_validator

SENIORITY_ORDER = [
    "Intern",
    "Entry Level",
    "Junior",
    "Mid Level",
    "Senior",
    "Lead",
    "Staff",
    "Principal",
    "Manager",
    "Director",
    "Unknown",
]

REMOTE_TYPES = ["Remote", "Hybrid", "Onsite", "Unknown"]
EMPLOYMENT_TYPES = [
    "Internship",
    "Part-time",
    "Contract",
    "Full-time",
    "Temporary",
    "Unknown",
]
EVIDENCE_UNKNOWN = "Unknown"


class LocationItem(BaseModel):
    """A structured location for a job posting."""

    display_name: str
    city: str | None = None
    state: str | None = None
    country_code: str | None = None
    normalized_key: str | None = None
    rank: int = 0

    @field_validator("country_code")
    @classmethod
    def _upper_country(cls, v: str | None) -> str | None:
        return v.upper() if v else None


class SkillItem(BaseModel):
    """A detected skill within a job posting."""

    name: str
    category: str | None = None
    matched_text: str = ""


class JobRecord(BaseModel):
    """A fully transformed, validated job record ready for persistence."""

    source: str
    external_job_id: str | None = None
    title: str
    original_title: str
    company: str
    company_normalized: str
    company_external_id: str | None = None
    locations: list[LocationItem] = Field(default_factory=list)
    description: str = ""
    employment_type: str = EVIDENCE_UNKNOWN
    seniority: str = EVIDENCE_UNKNOWN
    remote_type: str = EVIDENCE_UNKNOWN
    job_url: str
    apply_url: str | None = None
    posted_at: datetime | None = None
    scraped_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    salary_min: float | None = None
    salary_max: float | None = None
    salary_currency: str | None = None
    skills: list[SkillItem] = Field(default_factory=list)
    dedupe_key: str = ""
    raw_payload: dict[str, Any] | None = None


class RawRecord(BaseModel):
    """A validated raw record coming straight from an extractor.

    ``google_careers`` records carry the structured fields the source exposes
    (including HTML fragments); file-based sources map their columns onto the
    same shape. ``meta`` holds extractor bookkeeping.
    """

    model_config = {"extra": "allow"}

    source: str
    title: str | None = None
    external_job_id: str | None = None
    company: str | None = None
    company_external_id: str | None = None
    locations: list[dict[str, Any]] = Field(default_factory=list)
    description: str | None = None
    description_html: str | None = None
    overview_html: str | None = None
    qualifications_html: str | None = None
    additional_qualifications_html: str | None = None
    job_url: str | None = None
    apply_url: str | None = None
    posted_at: datetime | None = None
    scraped_at: datetime | None = None
    payload: dict[str, Any] | None = None