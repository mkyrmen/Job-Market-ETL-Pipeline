"""Pandas-based reporting artifacts.

After each load the pipeline can emit tidy CSV reports under
``data/processed/`` (git-ignored). This demonstrates the pandas stage of the
ETL stack while producing analyst-friendly deliverables.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from src.config import PROCESSED_DATA_DIR
from src.models import JobRecord

logger = logging.getLogger(__name__)


def jobs_to_tidy_frame(jobs: list[JobRecord]) -> pd.DataFrame:
    """Build a tidy, analyst-friendly DataFrame from job records."""
    rows = []
    for job in jobs:
        rows.append(
            {
                "source": job.source,
                "external_job_id": job.external_job_id,
                "title": job.title,
                "original_title": job.original_title,
                "company": job.company,
                "primary_location": job.locations[0].display_name if job.locations else None,
                "all_locations": "; ".join(l.display_name for l in job.locations),
                "seniority": job.seniority,
                "employment_type": job.employment_type,
                "remote_type": job.remote_type,
                "job_url": job.job_url,
                "posted_at": job.posted_at.isoformat() if job.posted_at else None,
                "scraped_at": job.scraped_at.isoformat() if job.scraped_at else None,
                "salary_min": job.salary_min,
                "salary_max": job.salary_max,
                "salary_currency": job.salary_currency,
                "skills": "; ".join(s.name for s in job.skills),
                "skill_count": len(job.skills),
            }
        )
    return pd.DataFrame(rows)


def skills_long_frame(jobs: list[JobRecord]) -> pd.DataFrame:
    """One row per (job, detected skill)."""
    rows = []
    for job in jobs:
        for skill in job.skills:
            rows.append(
                {
                    "external_job_id": job.external_job_id,
                    "title": job.title,
                    "skill": skill.name,
                    "category": skill.category,
                }
            )
    return pd.DataFrame(rows, columns=["external_job_id", "title", "skill", "category"])


def export_artifacts(jobs: list[JobRecord], outdir: str | Path | None = None) -> list[Path]:
    """Write tidy CSV reports for a job batch; returns written paths."""
    outdir = Path(outdir or PROCESSED_DATA_DIR)
    outdir.mkdir(parents=True, exist_ok=True)

    tidy = jobs_to_tidy_frame(jobs)
    tidy_path = outdir / "jobs_tidy.csv"
    tidy.to_csv(tidy_path, index=False)

    long = skills_long_frame(jobs)
    skills_path = outdir / "job_skills_long.csv"
    long.to_csv(skills_path, index=False)

    if not long.empty:
        summary = long.groupby(["skill", "category"]).size().reset_index(name="job_count")
        summary = summary.sort_values("job_count", ascending=False)
        top_path = outdir / "top_skills.csv"
        summary.to_csv(top_path, index=False)
    else:
        top_path = outdir / "top_skills.csv"
        top_path.write_text("skill,category,job_count\n", encoding="utf-8")

    logger.info("Exported pandas artifacts to %s: %s, %s, %s", outdir, tidy_path, skills_path, top_path)
    return [tidy_path, skills_path, top_path]