#!/usr/bin/env python
"""Seed the persistence layer from the bundled raw dataset(s).

Usage:
    python scripts/seed_database.py                       # -> local SQLite
    python scripts/seed_database.py --target supabase --file path.json
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import RAW_DATA_DIR, ensure_directories
from src.logging_config import configure_logging
from src.pipeline import run_etl


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", default=None, help="JSON/CSV raw records")
    parser.add_argument("--target", default="sqlite", choices=["sqlite", "supabase"])
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    configure_logging(verbose=args.verbose)
    ensure_directories()

    input_file = args.file or str(RAW_DATA_DIR / "google_careers_sample.json")
    if not Path(input_file).exists():
        print(f"No dataset found at {input_file}. Run scripts/export_sample_dataset.py first.",
              file=sys.stderr)
        return 1

    summary = run_etl(
        query="seed",
        source="json",
        input_file=input_file,
        target=args.target,
        dry_run=args.dry_run,
    )
    if args.dry_run:
        print(f"DRY-RUN  extracted={summary['records_extracted']} would_insert={summary['records_to_insert']}")
    else:
        print(
            f"SEED DONE extracted={summary['records_extracted']} inserted={summary.get('records_inserted', 0)} "
            f"duplicates_db={summary.get('duplicates_skipped_db', 0)}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())