"""End-to-end ETL orchestration.

Pipeline flow: extract -> validate -> transform -> dedupe -> load. The
scraper executes exactly once per invocation; duplicate prevention is
enforced both in memory (dedupe keys) and by database constraints.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from src.config import RAW_DATA_DIR, get_settings
from src.extract.base import ExtractionResult
from src.extract.file_loader import extract_from_csv, extract_from_json
from src.extract.google_careers import GoogleCareersExtractor
from src.load.sqlite_loader import SQLiteLoader
from src.models import JobRecord, RawRecord
from src.transform.dedupe import deduplicate
from src.transform.pipeline import transform_all
from src.validation.validators import validate_raw_records

logger = logging.getLogger(__name__)


def extract_records(
    query: str,
    limit: int | None = None,
    source: str = "google",
    input_file: str | None = None,
) -> ExtractionResult:
    """Dispatch to the requested extraction source."""
    if source in ("google", "google_careers") and input_file:
        path = Path(input_file)
        if path.suffix.lower() == ".csv":
            return extract_from_csv(path, query=query)
        return extract_from_json(path, query=query)
    if source in ("json",):
        path = Path(input_file) if input_file else RAW_DATA_DIR / "google_careers_sample.json"
        return extract_from_json(path, query=query)
    if source in ("csv",):
        if not input_file:
            raise ValueError("--input is required for source=csv")
        return extract_from_csv(Path(input_file), query=query)
    if source in ("google", "google_careers"):
        return GoogleCareersExtractor().extract(query=query, limit=limit)
    raise ValueError(f"Unknown source: {source}")


def run_etl(
    *,
    query: str,
    limit: int | None = None,
    source: str = "google",
    input_file: str | None = None,
    target: str = "sqlite",
    dry_run: bool = False,
    export_path: str | None = None,
) -> dict:
    """Run one full ETL pass and return a summary dictionary."""
    settings = get_settings()
    started = datetime.now(timezone.utc)
    summary: dict = {
        "status": "ok", "query": query, "source": source, "started_at": started.isoformat(),
    }

    # 1. Extract
    extract_result = extract_records(query, limit, source, input_file)
    summary["records_extracted"] = len(extract_result.records)

    # 2. Validate
    valid_raw, errors = validate_raw_records(extract_result.records)
    summary["validation_failures"] = len(errors)
    if errors:
        logger.warning("Validation dropped %d invalid records", len(errors))
        for _original, reason in errors[:5]:
            logger.warning("  invalid record: %s", reason)

    # 3. Transform
    jobs: list[JobRecord] = transform_all(valid_raw)

    # 4. Deduplicate within this run (first occurrence wins)
    jobs, dropped_in_memory = deduplicate(jobs)
    summary["duplicates_in_run"] = dropped_in_memory

    # 5. Optional export of raw records (for sample datasets)
    if export_path:
        out = Path(export_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open("w", encoding="utf-8") as fh:
            json.dump(extract_result.records, fh, ensure_ascii=False, indent=2, default=str)
        summary["export_path"] = str(out)

    if dry_run:
        summary["status"] = "dry-run"
        summary["dry_run"] = True
        summary["records_to_insert"] = len(jobs)
        summary["finished_at"] = datetime.now(timezone.utc).isoformat()
        logger.info(
            "DRY RUN: %d records extracted, %d would be inserted",
            summary["records_extracted"], len(jobs),
        )
        return summary

    # 6. Load
    loader = _build_loader(target)
    try:
        load_result = loader.upsert_jobs(jobs)
        summary["records_inserted"] = load_result.inserted
        summary["duplicates_skipped_db"] = load_result.duplicates_skipped
        summary["load_errors"] = load_result.errors
        summary["finished_at"] = datetime.now(timezone.utc).isoformat()
    finally:
        loader.close()

    # 7. Pandas reporting artifacts (local target only)
    if not dry_run and summary.get("records_inserted", 0) > 0 and target != "supabase":
        try:
            from src.reporting import export_artifacts

            summary["artifacts"] = [str(p) for p in export_artifacts(jobs)]
        except Exception:  # noqa: BLE001 - artifact export is non-critical
            logger.exception("Could not export pandas artifacts")

    logger.info(
        "ETL complete: %d extracted, %d inserted, %d duplicates skipped (db), %d dropped in-run",
        summary["records_extracted"], load_result.inserted,
        load_result.duplicates_skipped, dropped_in_memory,
    )
    return summary


def _build_loader(target: str):
    if target == "supabase":
        from src.load.supabase_loader import SupabaseLoader

        return SupabaseLoader()
    return SQLiteLoader(get_settings().database_path)


def load_legacy_jobs(jobs: list[JobRecord], target: str = "sqlite") -> None:
    """Load pre-transformed records (used by the migration path)."""
    loader = _build_loader(target)
    try:
        result = loader.upsert_jobs(jobs)
        logger.info(
            "Loaded %d migrated jobs (%d duplicates skipped)",
            result.inserted, result.duplicates_skipped,
        )
    finally:
        loader.close()