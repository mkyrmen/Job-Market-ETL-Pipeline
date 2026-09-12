"""Migration of the original SQLite database into the new schema.

The original scraper wrote to a flat ``jobs(query, title, description,
scraped_at)`` table. This module:

1. Archives the legacy database (data preservation) into ``data/processed/``.
2. Reads legacy rows, cleans the noisy body-text descriptions.
3. Re-uses the normal transformation pipeline.
4. Loads the migrated records into the new normalised schema (SQLite and/or
   Supabase). Rows duplicated by the old double-execution bug are collapsed
   via the dedupe-key fingerprint.
"""

from __future__ import annotations

import logging
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

from src.config import PROCESSED_DATA_DIR, get_settings
from src.models import RawRecord
from src.pipeline import load_legacy_jobs
from src.transform.cleaners import collapse_whitespace
from src.transform.pipeline import transform_all

logger = logging.getLogger(__name__)

LEGACY_ARCHIVE_NAME = "legacy_jobs_database_archive.db"


def is_legacy_schema(path: str | Path) -> bool:
    """True when *path* holds the original 4-column ``jobs`` table."""
    try:
        conn = sqlite3.connect(str(path))
    except sqlite3.Error:
        return False
    try:
        row = conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='jobs'"
        ).fetchone()
        return bool(row and "dedupe_key" not in (row[0] or ""))
    finally:
        conn.close()


def archive_legacy_database(legacy_path: str | Path) -> Path:
    """Copy the legacy DB to the processed archive, preserving it forever."""
    legacy_path = Path(legacy_path)
    PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)
    archive = PROCESSED_DATA_DIR / LEGACY_ARCHIVE_NAME
    if legacy_path.exists() and not archive.exists():
        shutil.copy2(legacy_path, archive)
        logger.info("Archived legacy database to %s", archive)
    return archive


def read_legacy_jobs(legacy_path: str | Path) -> list[dict]:
    """Read legacy jobs, deduplicated by normalised title (first wins)."""
    conn = sqlite3.connect(str(legacy_path))
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT query, title, description, scraped_at FROM jobs ORDER BY scraped_at ASC"
    ).fetchall()
    conn.close()

    seen: set[str] = set()
    records: list[dict] = []
    for row in rows:
        title = collapse_whitespace(row["title"] or "")
        key = title.lower()
        if not title or key in seen:
            continue
        seen.add(key)
        try:
            scraped_at = datetime.fromisoformat(row["scraped_at"])
        except (TypeError, ValueError):
            scraped_at = None
        records.append(
            {
                "source": "google_careers_legacy",
                "title": title,
                "company": "Google",
                "description": collapse_whitespace(row["description"] or ""),
                "scraped_at": scraped_at,
            }
        )
    logger.info("Read %d unique legacy job(s)", len(records))
    return records


def migrate_legacy_database(
    legacy_path: str | Path,
    *,
    target: str = "sqlite",
) -> dict:
    """Migrate the legacy SQLite database into the new normalised schema."""
    legacy_path = Path(legacy_path)
    settings = get_settings()

    if not is_legacy_schema(legacy_path):
        raise ValueError(
            f"{legacy_path} does not use the legacy 4-column 'jobs' schema; "
            "nothing to migrate."
        )

    raw_dicts = read_legacy_jobs(legacy_path)
    jobs = transform_all([RawRecord.model_validate(r) for r in raw_dicts])
    archive = archive_legacy_database(legacy_path)

    if target == "sqlite":
        target_path = Path(settings.database_path)
        if target_path.resolve().as_posix().lower() == legacy_path.resolve().as_posix().lower():
            # The archived copy preserves the legacy data; start fresh at the
            # current path so the new normalised schema can be created there.
            legacy_path.unlink()

    load_legacy_jobs(jobs, target=target)

    return {
        "legacy_archive": str(archive),
        "legacy_rows_read": len(raw_dicts),
        "migrated_jobs": len(jobs),
    }