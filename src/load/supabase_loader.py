"""Supabase (PostgreSQL) persistence backend.

Uses the PostgREST client with the *service role* key, which must never be
exposed to the browser. Reads for the public web application use the anon
key from Next.js server-side routes.

Operations are batched: dimensions (companies, locations, skills, sources)
are resolved once per run, and only unknown rows are inserted. Jobs are
deduplicated against existing ``dedupe_key`` values before insertion.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from src.config import get_settings
from src.load.base import LoadResult
from src.models import JobRecord

logger = logging.getLogger(__name__)

_BATCH_SIZE = 200
_DIM_BATCH = 300


class SupabaseLoader:
    """Supabase REST loader."""

    def __init__(self) -> None:
        settings = get_settings()
        if not settings.supabase_configured:
            raise RuntimeError(
                "Supabase is not configured (set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY)"
            )
        from supabase import create_client

        self._client = create_client(
            settings.supabase_url, settings.supabase_service_role_key
        )
        self.client = self._client

    # -- batch helpers -----------------------------------------------------

    @staticmethod
    def _chunks(items: list, size: int):
        for i in range(0, len(items), size):
            yield items[i : i + size]

    def _existing(self, table: str, key: str, values: list[str]) -> set[str]:
        if not values:
            return set()
        found: set[str] = set()
        for chunk in self._chunks(values, 800):
            resp = (
                self.client.table(table)
                .select(key)
                .in_(key, chunk)
                .execute()
            )
            found.update(row[key] for row in resp.data)
        return found

    def _insert_dims(self, table: str, rows: list[dict]) -> None:
        if not rows:
            return
        for chunk in self._chunks(rows, _DIM_BATCH):
            self.client.table(table).insert(chunk).execute()

    # -- main path ----------------------------------------------------------

    def upsert_jobs(self, jobs: list[JobRecord]) -> LoadResult:
        result = LoadResult()
        if not jobs:
            return result

        now = datetime.now(timezone.utc).isoformat()

        # Sources
        source_names = {job.source for job in jobs}
        existing_sources = self._existing("sources", "name", list(source_names))
        missing_sources = [
            {"name": name, "base_url": "https://www.google.com/about/careers", "created_at": now}
            for name in source_names - existing_sources
        ]
        self._insert_dims("sources", missing_sources)
        source_ids = {
            row["name"]: row["id"]
            for chunk in self._chunks(list(source_names), 800)
            for row in self.client.table("sources").select("id,name").in_("name", chunk).execute().data
        }

        # Companies
        company_rows = {
            job.company: {"name": job.company, "normalized_name": job.company_normalized,
                          "external_id": job.company_external_id}
            for job in jobs if job.company
        }
        existing_companies = self._existing("companies", "name", list(company_rows))
        self._insert_dims(
            "companies",
            [dict(v, created_at=now) for k, v in company_rows.items() if k not in existing_companies],
        )
        company_ids = {
            row["name"]: row["id"]
            for chunk in self._chunks(list(company_rows), 800)
            for row in self.client.table("companies").select("id,name").in_("name", chunk).execute().data
        }

        # Locations
        location_rows: dict[str, dict] = {}
        for job in jobs:
            for loc in job.locations:
                location_rows[loc.normalized_key] = {
                    "normalized_key": loc.normalized_key,
                    "display_name": loc.display_name,
                    "city": loc.city,
                    "state": loc.state,
                    "country_code": loc.country_code,
                }
        existing_locations = self._existing("locations", "normalized_key", list(location_rows))
        self._insert_dims(
            "locations",
            [dict(v, created_at=now) for k, v in location_rows.items() if k not in existing_locations],
        )
        location_ids = {
            row["normalized_key"]: row["id"]
            for chunk in self._chunks(list(location_rows), 800)
            for row in self.client.table("locations")
            .select("id,normalized_key").in_("normalized_key", chunk).execute().data
        }

        # Skills
        skill_rows: dict[str, dict] = {}
        for job in jobs:
            for skill in job.skills:
                skill_rows[skill.name] = {"name": skill.name, "category": skill.category}
        existing_skills = self._existing("skills", "name", list(skill_rows))
        self._insert_dims(
            "skills",
            [dict(v, created_at=now) for k, v in skill_rows.items() if k not in existing_skills],
        )
        skill_ids = {
            row["name"]: row["id"]
            for chunk in self._chunks(list(skill_rows), 800)
            for row in self.client.table("skills").select("id,name").in_("name", chunk).execute().data
        }

        # Jobs: skip existing dedupe keys
        existing_job_keys = self._existing("jobs", "dedupe_key", [job.dedupe_key for job in jobs])
        fresh = [job for job in jobs if job.dedupe_key not in existing_job_keys]
        result.duplicates_skipped = len(jobs) - len(fresh)

        job_row_map: dict[str, int] = {}
        for chunk in self._chunks(fresh, _BATCH_SIZE):
            rows = []
            for job in chunk:
                rows.append(
                    {
                        "source_id": source_ids.get(job.source),
                        "external_job_id": job.external_job_id,
                        "dedupe_key": job.dedupe_key,
                        "title": job.title,
                        "original_title": job.original_title,
                        "company_id": company_ids.get(job.company),
                        "description": job.description,
                        "employment_type": job.employment_type,
                        "seniority": job.seniority,
                        "remote_type": job.remote_type,
                        "job_url": job.job_url,
                        "apply_url": job.apply_url,
                        "posted_at": job.posted_at.isoformat() if job.posted_at else None,
                        "scraped_at": job.scraped_at.isoformat() if job.scraped_at else now,
                        "salary_min": job.salary_min,
                        "salary_max": job.salary_max,
                        "salary_currency": job.salary_currency,
                        "raw_payload": json.dumps(job.raw_payload) if job.raw_payload else None,
                        "created_at": now,
                    }
                )
            resp = self.client.table("jobs").insert(rows).select("id,dedupe_key").execute()
            for row in resp.data:
                job_row_map[row["dedupe_key"]] = row["id"]
            result.inserted += len(resp.data)

        # Job locations + skills
        job_location_rows = []
        job_skill_rows = []
        for job in fresh:
            job_id = job_row_map.get(job.dedupe_key)
            if job_id is None:
                continue
            job_location_rows.extend(
                {"job_id": job_id, "location_id": location_ids[loc.normalized_key], "rank": loc.rank}
                for loc in job.locations if loc.normalized_key in location_ids
            )
            job_skill_rows.extend(
                {"job_id": job_id, "skill_id": skill_ids[skill.name], "matched_text": skill.matched_text}
                for skill in job.skills if skill.name in skill_ids
            )
        for chunk in self._chunks(job_location_rows, _BATCH_SIZE):
            try:
                self.client.table("job_locations").insert(chunk).execute()
            except Exception:  # noqa: BLE001
                logger.warning("Some job_locations rows failed; continuing")
                result.errors += 1
        for chunk in self._chunks(job_skill_rows, _BATCH_SIZE):
            try:
                self.client.table("job_skills").insert(chunk).execute()
            except Exception:  # noqa: BLE001
                logger.warning("Some job_skills rows failed; continuing")
                result.errors += 1

        logger.info(
            "Supabase upsert: %d inserted, %d duplicates skipped",
            result.inserted, result.duplicates_skipped,
        )
        return result

    # -- extraction run bookkeeping -----------------------------------

    def start_run(self, query: str) -> int:
        resp = (
            self.client.table("extraction_runs")
            .insert({"query": query, "status": "running", "started_at": datetime.now(timezone.utc).isoformat()})
            .select("id")
            .execute()
        )
        return resp.data[0]["id"] if resp.data else 0

    def finish_run(
        self,
        run_id: int,
        *,
        status: str,
        extracted: int,
        inserted: int,
        skipped: int,
        error: str | None = None,
    ) -> None:
        if run_id:
            self.client.table("extraction_runs").update(
                {
                    "status": status,
                    "records_extracted": extracted,
                    "records_inserted": inserted,
                    "duplicates_skipped": skipped,
                    "finished_at": datetime.now(timezone.utc).isoformat(),
                    "error": error,
                }
            ).eq("id", run_id).execute()

    def close(self) -> None:
        """PostgREST clients are stateless; nothing to release."""