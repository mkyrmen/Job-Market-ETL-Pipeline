#!/usr/bin/env python
"""Migrate the original (legacy) SQLite database into the new schema.

The legacy database is archived to ``data/processed/``, then its (deduplicated)
rows are transformed through the normal pipeline and loaded into the chosen
target (SQLite local DB or Supabase).

Usage:
    python scripts/migrate_sqlite_to_postgres.py                 # -> local SQLite
    python scripts/migrate_sqlite_to_postgres.py --target supabase
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import ensure_directories, get_settings
from src.logging_config import configure_logging


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--legacy-path", default=None, help="Path to the legacy jobs_database.db")
    parser.add_argument("--target", default="sqlite", choices=["sqlite", "supabase"])
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    configure_logging(verbose=args.verbose)
    ensure_directories()

    from src.migration import migrate_legacy_database

    legacy_path = Path(args.legacy_path or get_settings().database_path)
    if not legacy_path.exists():
        print(f"Legacy database not found: {legacy_path}", file=sys.stderr)
        return 1

    result = migrate_legacy_database(legacy_path, target=args.target)
    print(
        f"Migrated {result['migrated_jobs']} job(s) to target={args.target}.\n"
        f"  legacy rows read : {result['legacy_rows_read']}\n"
        f"  archive          : {result['legacy_archive']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())