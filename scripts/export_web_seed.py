r"""Export the local SQLite database into a web-friendly JSON snapshot.

The snapshot is a single deterministic JSON file (committed to the repo)
that the Next.js web app can read when Supabase is not configured, and that
serves as a stable fixture for local development and CI.

Usage:
    .\.venv\Scripts\python.exe scripts\export_web_seed.py [--out data/web_seed.json]
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))


def _iso(value) -> str | None:
    if value is None:
        return None
    return value.isoformat() if isinstance(value, datetime) else str(value)


def export(conn: sqlite3.Connection) -> dict:
    conn.row_factory = sqlite3.Row

    jobs = []
    job_columns = [
        r["name"] for r in conn.execute("PRAGMA table_info(jobs)")
        if r["name"] != "raw_payload"
    ]
    sql = "SELECT {cols} FROM jobs ORDER BY external_job_id".format(
        cols=", ".join(job_columns)
    )
    for row in conn.execute(sql):
        job = dict(row)
        job["posted_at"] = _iso(job.get("posted_at"))
        job["scraped_at"] = _iso(job.get("scraped_at"))
        job["created_at"] = _iso(job.get("created_at"))
        job["updated_at"] = _iso(job.get("updated_at"))

        locs = conn.execute(
            """
            SELECT l.display_name, l.city, l.state, l.country_code, l.normalized_key, jl.rank
            FROM job_locations jl
            JOIN locations l ON l.id = jl.location_id
            WHERE jl.job_id = ? ORDER BY jl.rank
            """,
            (row["id"],),
        ).fetchall()
        job["locations"] = [dict(l) for l in locs]

        skills = conn.execute(
            """
            SELECT s.name, s.category, js.matched_text
            FROM job_skills js
            JOIN skills s ON s.id = js.skill_id
            WHERE js.job_id = ? ORDER BY s.name
            """,
            (row["id"],),
        ).fetchall()
        job["skills"] = [dict(s) for s in skills]

        companies = conn.execute(
            "SELECT name, normalized_name, external_id FROM companies WHERE id = ?",
            (row["company_id"],),
        ).fetchall()
        job["company"] = dict(companies[0]) if companies else None

        job.pop("dedupe_key", None)
        job.pop("company_id", None)
        jobs.append(job)

    return {
        "schema_version": 1,
        "source": "sqlite_export",
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "record_count": len(jobs),
        "records": jobs,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default=str(REPO_ROOT / "data" / "jobs_database.db"))
    parser.add_argument("--out", default=str(REPO_ROOT / "data" / "web_seed.json"))
    args = parser.parse_args()

    conn = sqlite3.connect(args.db)
    try:
        bundle = export(conn)
    finally:
        conn.close()

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(bundle, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Exported {bundle['record_count']} jobs -> {out}")


if __name__ == "__main__":
    main()