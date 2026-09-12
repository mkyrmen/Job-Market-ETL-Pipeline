#!/usr/bin/env python
"""Extract a curated, deduplicated sample dataset into ``data/raw/``.

The resulting JSON is committed so the analytics platform (and the web demo)
work before/without a live extraction. Records are real Google Careers
postings.

Usage:
    python scripts/export_sample_dataset.py            # default ~300 records
    python scripts/export_sample_dataset.py --limit 50
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import RAW_DATA_DIR

SEARCH_QUERIES = [
    "Data Analyst",
    "Software Engineer",
    "Data Scientist",
    "Machine Learning Engineer",
    "Product Manager",
    "Cloud Engineer",
    "DevOps Engineer",
    "Data Engineer",
    "Frontend Engineer",
    "UX Researcher",
    "Financial Analyst",
    "Intern",
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=300)
    parser.add_argument("--output", default=str(RAW_DATA_DIR / "google_careers_sample.json"))
    parser.add_argument("--queries", nargs="*", default=SEARCH_QUERIES)
    args = parser.parse_args()

    for path in (RAW_DATA_DIR,):
        path.mkdir(parents=True, exist_ok=True)

    from src.pipeline import extract_records

    collected: dict[str, dict] = {}
    per_query = max(1, args.limit // len(args.queries))
    for query in args.queries:
        try:
            result = extract_records(query, limit=per_query, source="google")
        except Exception as exc:  # noqa: BLE001
            print(f"WARN: extraction failed for '{query}': {exc}", file=sys.stderr)
            continue
        for record in result.records:
            collected[record["external_job_id"]] = record
        print(f"{query!r}: {len(result.records)} records fetched")

    records = sorted(collected.values(), key=lambda r: r["external_job_id"])
    # Trim to the requested size deterministically.
    records = records[: args.limit]

    payload = {
        "schema_version": 1,
        "source": "google_careers",
        "exported_at": datetime.utcnow().isoformat(),
        "record_count": len(records),
        "records": records,
    }
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(f"Exported {len(records)} records to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())