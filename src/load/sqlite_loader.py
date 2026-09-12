"""SQLite persistence backend (local development/staging).

Implements the same normalised relational schema as the PostgreSQL
production target so analytics behave identically on both backends.
Duplicates are prevented with a UNIQUE ``dedupe_key`` and a UNIQUE
``(source_id, external_job_id)`` constraint.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from src.load.base import LoadResult
from src.models import JobRecord

logger = logging.getLogger(__name__)

SCHEMA = """
CREATE TABLE IF NOT EXISTS sources (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL UNIQUE,
    base_url    TEXT,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS companies (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    external_id     TEXT UNIQUE,
    name            TEXT NOT NULL UNIQUE,
    normalized_name TEXT NOT NULL,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS locations (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    normalized_key TEXT NOT NULL UNIQUE,
    display_name   TEXT NOT NULL,
    city           TEXT,
    state          TEXT,
    country_code   TEXT,
    created_at     TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS skills (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT NOT NULL UNIQUE,
    category   TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS jobs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id       INTEGER NOT NULL REFERENCES sources(id),
    external_job_id TEXT,
    dedupe_key      TEXT NOT NULL UNIQUE,
    title           TEXT NOT NULL,
    original_title  TEXT,
    company_id      INTEGER REFERENCES companies(id),
    description     TEXT,
    employment_type TEXT,
    seniority       TEXT,
    remote_type     TEXT,
    job_url         TEXT,
    apply_url       TEXT,
    posted_at       TEXT,
    scraped_at      TEXT NOT NULL,
    salary_min      REAL,
    salary_max      REAL,
    salary_currency TEXT,
    raw_payload     TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (source_id, external_job_id)
);
CREATE INDEX IF NOT EXISTS idx_jobs_title     ON jobs(title);
CREATE INDEX IF NOT EXISTS idx_jobs_company   ON jobs(company_id);
CREATE INDEX IF NOT EXISTS idx_jobs_seniority ON jobs(seniority);
CREATE INDEX IF NOT EXISTS idx_jobs_remote    ON jobs(remote_type);
CREATE INDEX IF NOT EXISTS idx_jobs_posted    ON jobs(posted_at);
CREATE INDEX IF NOT EXISTS idx_jobs_scraped   ON jobs(scraped_at);

CREATE TABLE IF NOT EXISTS job_locations (
    job_id      INTEGER NOT NULL REFERENCES jobs(id),
    location_id INTEGER NOT NULL REFERENCES locations(id),
    rank        INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (job_id, location_id)
);

CREATE TABLE IF NOT EXISTS job_skills (
    job_id       INTEGER NOT NULL REFERENCES jobs(id),
    skill_id     INTEGER NOT NULL REFERENCES skills(id),
    matched_text TEXT,
    PRIMARY KEY (job_id, skill_id)
);
CREATE INDEX IF NOT EXISTS idx_job_skills_skill ON job_skills(skill_id);

CREATE TABLE IF NOT EXISTS extraction_runs (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id         INTEGER REFERENCES sources(id),
    query             TEXT,
    status            TEXT,
    records_extracted INTEGER,
    records_inserted  INTEGER,
    duplicates_skipped INTEGER,
    started_at        TEXT,
    finished_at       TEXT,
    error             TEXT
);
"""


def _iso(dt: datetime | None) -> str | None:
    return dt.isoformat() if dt else None


class SQLiteLoader:
    """Normalised-schema loader over a local SQLite database."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    # -- dimension lookups / upserts -------------------------------------

    def get_or_create_source(self, name: str, base_url: str | None = None) -> int:
        row = self.conn.execute("SELECT id FROM sources WHERE name = ?", (name,)).fetchone()
        if row:
            return row["id"]
        cur = self.conn.execute(
            "INSERT OR IGNORE INTO sources (name, base_url) VALUES (?, ?)", (name, base_url)
        )
        return self.conn.execute("SELECT id FROM sources WHERE name = ?", (name,)).fetchone()["id"]

    def get_or_create_company(self, name: str, normalized: str, external_id: str | None) -> int:
        row = self.conn.execute("SELECT id FROM companies WHERE name = ?", (name,)).fetchone()
        if row:
            return row["id"]
        self.conn.execute(
            "INSERT OR IGNORE INTO companies (name, normalized_name, external_id) VALUES (?, ?, ?)",
            (name, normalized, external_id),
        )
        return self.conn.execute("SELECT id FROM companies WHERE name = ?", (name,)).fetchone()["id"]

    def get_or_create_location(self, key: str, display: str, city, state, country) -> int:
        row = self.conn.execute("SELECT id FROM locations WHERE normalized_key = ?", (key,)).fetchone()
        if row:
            return row["id"]
        self.conn.execute(
            "INSERT OR IGNORE INTO locations (normalized_key, display_name, city, state, country_code) "
            "VALUES (?, ?, ?, ?, ?)",
            (key, display, city, state, country),
        )
        return self.conn.execute("SELECT id FROM locations WHERE normalized_key = ?", (key,)).fetchone()["id"]

    def get_or_create_skill(self, name: str, category: str | None) -> int:
        row = self.conn.execute("SELECT id FROM skills WHERE name = ?", (name,)).fetchone()
        if row:
            return row["id"]
        self.conn.execute(
            "INSERT OR IGNORE INTO skills (name, category) VALUES (?, ?)", (name, category)
        )
        return self.conn.execute("SELECT id FROM skills WHERE name = ?", (name,)).fetchone()["id"]

    # -- main path --------------------------------------------------------

    def upsert_jobs(self, jobs: list[JobRecord]) -> LoadResult:
        result = LoadResult()
        source_cache: dict[str, int] = {}

        for job in jobs:
            try:
                source_id = source_cache.get(job.source)
                if source_id is None:
                    source_id = self.get_or_create_source(job.source, "https://www.google.com/about/careers")
                    source_cache[job.source] = source_id
                self._upsert_job(job, source_id, result)
            except sqlite3.Error as exc:
                result.errors += 1
                logger.error("SQLite error persisting job %s: %s", job.external_job_id, exc)
        self.conn.commit()
        return result

    def _upsert_job(self, job: JobRecord, source_id: int, result: LoadResult) -> None:
        existing = self.conn.execute(
            "SELECT id FROM jobs WHERE dedupe_key = ?", (job.dedupe_key,)
        ).fetchone()
        if existing:
            result.duplicates_skipped += 1
            return

        company_id = None
        if job.company:
            company_id = self.get_or_create_company(
                job.company, job.company_normalized, job.company_external_id
            )

        cur = self.conn.execute(
            """INSERT INTO jobs (source_id, external_job_id, dedupe_key, title, original_title,
                                 company_id, description, employment_type, seniority, remote_type,
                                 job_url, apply_url, posted_at, scraped_at, salary_min, salary_max,
                                 salary_currency, raw_payload)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                source_id,
                job.external_job_id,
                job.dedupe_key,
                job.title,
                job.original_title,
                company_id,
                job.description,
                job.employment_type,
                job.seniority,
                job.remote_type,
                job.job_url,
                job.apply_url,
                _iso(job.posted_at),
                _iso(job.scraped_at),
                job.salary_min,
                job.salary_max,
                job.salary_currency,
                json.dumps(job.raw_payload) if job.raw_payload else None,
            ),
        )
        job_id = cur.lastrowid
        result.inserted += 1

        for loc in job.locations:
            location_id = self.get_or_create_location(
                loc.normalized_key, loc.display_name, loc.city, loc.state, loc.country_code
            )
            self.conn.execute(
                "INSERT OR IGNORE INTO job_locations (job_id, location_id, rank) VALUES (?, ?, ?)",
                (job_id, location_id, loc.rank),
            )
        for skill in job.skills:
            skill_id = self.get_or_create_skill(skill.name, skill.category)
            self.conn.execute(
                "INSERT OR IGNORE INTO job_skills (job_id, skill_id, matched_text) VALUES (?, ?, ?)",
                (job_id, skill_id, skill.matched_text),
            )

    # -- extraction run bookkeeping --------------------------------------

    def start_extraction_run(self, source_id: int | None, query: str) -> int:
        cur = self.conn.execute(
            "INSERT INTO extraction_runs (source_id, query, status, started_at) VALUES (?, ?, ?, ?)",
            (source_id, query, "running", _iso(datetime.now(timezone.utc))),
        )
        return cur.lastrowid

    def finish_extraction_run(self, run_id: int, *, status: str, extracted: int, inserted: int, skipped: int, error: str | None = None) -> None:
        self.conn.execute(
            """UPDATE extraction_runs
               SET status = ?, records_extracted = ?, records_inserted = ?,
                   duplicates_skipped = ?, finished_at = ?, error = ?
               WHERE id = ?""",
            (status, extracted, inserted, skipped, _iso(datetime.now(timezone.utc)), error, run_id),
        )

    def close(self) -> None:
        self.conn.close()