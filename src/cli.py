"""Command-line interface for the ETL pipeline.

Usage examples
--------------
    python -m src.main run --query "Data Analyst" --limit 100
    python -m src.main run --query "Software Engineer" --headless --target supabase
    python -m src.main run --source json --input data/raw/google_careers_sample.json --dry-run
    python -m src.main analyze
    python -m src.main migrate
    python -m src.main seed
    python -m src.main export-sample --query "Data Analyst" --limit 300 --output data/raw/google_careers_sample.json
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

from src.analytics import compute_insights
from src.analytics.engine import AnalyticsEngine
from src.config import RAW_DATA_DIR, ensure_directories, get_settings
from src.extract.selenium_collector import SeleniumGoogleCareersCollector
from src.logging_config import configure_logging

logger = logging.getLogger("jmip")


def _add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--verbose", action="store_true", help="Enable DEBUG logging")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="jmip",
        description="Job Market Intelligence Platform — data pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--version", action="store_true", help="Print version and exit")
    sub = parser.add_subparsers(dest="command", required=False)

    # run
    run = sub.add_parser("run", help="Run one ETL pass (extract -> validate -> transform -> load)")
    run.add_argument("--query", default="Data Analyst", help="Search query for the source (default: Data Analyst)")
    run.add_argument("--source", default="google", choices=["google", "json", "csv"], help="Extraction source")
    run.add_argument("--input", help="Input file for source=json/csv")
    run.add_argument("--limit", type=int, default=None, help="Maximum records to extract")
    run.add_argument("--target", default="sqlite", choices=["sqlite", "supabase"], help="Persistence target")
    run.add_argument("--driver", default="http", choices=["http", "selenium"], help="Google source transport")
    run.add_argument("--headless", action="store_true", help="Headless Chrome (selenium driver)")
    run.add_argument("--dry-run", action="store_true", help="Extract/transform but do not persist")
    run.add_argument("--export", help="Write extracted raw records to a JSON file")
    _add_common(run)

    # analyze
    analyze = sub.add_parser("analyze", help="Run analytics against the local database")
    analyze.add_argument("--json", action="store_true", help="Emit JSON instead of a text report")
    _add_common(analyze)

    # migrate
    migrate = sub.add_parser("migrate", help="Migrate the legacy SQLite database into the new schema")
    migrate.add_argument("--legacy-path", default=None, help="Path to the legacy jobs_database.db")
    migrate.add_argument("--target", default="sqlite", choices=["sqlite", "supabase"], help="Migration target")
    _add_common(migrate)

    # seed
    seed = sub.add_parser("seed", help="Load the bundled sample dataset into the target")
    seed.add_argument("--file", default=None, help="JSON/CSV records file (default: bundled sample)")
    seed.add_argument("--target", default="sqlite", choices=["sqlite", "supabase"], help="Persistence target")
    seed.add_argument("--dry-run", action="store_true", help="Report without persisting")
    _add_common(seed)

    # export-sample
    export = sub.add_parser("export-sample", help="Extract raw records to a JSON sample dataset")
    export.add_argument("--query", default="Data Analyst")
    export.add_argument("--limit", type=int, default=100)
    export.add_argument("--output", default=None, help="Target path")
    _add_common(export)

    return parser


# -------------------------------------------------------------------------


def cmd_run(args: argparse.Namespace) -> None:
    from src.pipeline import run_etl

    source = args.source
    input_file = args.input
    if args.driver == "selenium" and args.source == "google":
        settings = get_settings()
        collector = SeleniumGoogleCareersCollector(headless=args.headless)
        result = collector.extract(query=args.query, limit=args.limit)
        from src.config import RAW_DATA_DIR

        Path(input_file or RAW_DATA_DIR / "_selenium_tmp.json").write_text(
            json.dumps(result.records, ensure_ascii=False, default=str), encoding="utf-8"
        )
        source, input_file = "json", input_file or str(RAW_DATA_DIR / "_selenium_tmp.json")

    summary = run_etl(
        query=args.query,
        limit=args.limit,
        source=source,
        input_file=input_file,
        target=args.target,
        dry_run=args.dry_run,
        export_path=args.export,
    )
    if args.dry_run:
        print(f"DRY-RUN  extracted={summary['records_extracted']} would_insert={summary['records_to_insert']}")
    else:
        print(
            f"ETL DONE extract={summary['records_extracted']} insert={summary.get('records_inserted', 0)} "
            f"duplicates_db={summary.get('duplicates_skipped_db', 0)} "
            f"duplicates_run={summary.get('duplicates_in_run', 0)} "
            f"target={args.target}"
        )


def cmd_analyze(args: argparse.Namespace) -> None:
    settings = get_settings()
    import sqlite3

    conn = sqlite3.connect(settings.database_path)
    conn.row_factory = sqlite3.Row
    try:
        engine = AnalyticsEngine(conn)
        bundle = {
            "overview": engine.overview(),
            "jobs_by_seniority": engine.jobs_by_seniority(),
            "jobs_by_employment_type": engine.jobs_by_employment_type(),
            "jobs_by_remote_type": engine.jobs_by_remote_type(),
            "jobs_by_company": engine.jobs_by_company(),
            "jobs_by_location": engine.jobs_by_location(),
            "jobs_over_time": engine.jobs_over_time(),
            "jobs_by_country": engine.jobs_by_country(),
            "top_skills": engine.top_skills(),
            "skill_combinations": engine.skill_combinations(),
            "skills_by_seniority": engine.skills_by_seniority(),
            "skill_trends": engine.skill_trends(),
            "seniority_over_time": engine.seniority_over_time(),
        }
        if args.json:
            print(json.dumps(bundle, indent=2, default=str))
        else:
            overview = bundle["overview"]
            print("=" * 62)
            print(f"{'JOB MARKET INTELLIGENCE — ANALYTICS REPORT':^62}")
            print(f"{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC'):^62}")
            print("=" * 62)
            print(f"Total jobs:      {overview['total_jobs']}")
            print(f"Companies:       {overview['total_companies']}")
            print(f"Locations:       {overview['total_locations']}")
            print(f"Skills:          {overview['total_skills']}")
            print(f"Sources:         {overview['total_sources']}")
            print(f"Most demanded:   {overview['most_demanded_skill']} "
                  f"({overview['most_demanded_skill_jobs']} jobs)")
            if overview.get("salary"):
                s = overview["salary"]
                print(f"Salary disclosed: {s['count']} postings, "
                      f"${int(s['min_salary']):,} - ${int(s['max_salary']):,}")
            print("-" * 62)
            print("Seniority", "   Count")
            for row in bundle["jobs_by_seniority"]:
                print(f"  {row['seniority']:<20} {row['count']}")
            print("-" * 62)
            print("Top skills (job demand)")
            for row in bundle["top_skills"][:10]:
                print(f"  {row['skill']:<28} {row['jobs']:>4}  {row['percentage']:>5}%")
            print("-" * 62)
            print("Insights")
            for insight in compute_insights(bundle):
                print(f"  • {insight['title']}")
                print(f"    {insight['text']}")
    finally:
        conn.close()


def cmd_migrate(args: argparse.Namespace) -> None:
    from src.migration import migrate_legacy_database

    legacy_path = args.legacy_path or get_settings().database_path
    result = migrate_legacy_database(legacy_path, target=args.target)
    print(
        f"Migrated {result['migrated_jobs']} job(s) from legacy DB "
        f"(archived to {result['legacy_archive']}) into target={args.target}"
    )


def cmd_seed(args: argparse.Namespace) -> None:
    from src.pipeline import run_etl

    input_file = args.file or str(
        RAW_DATA_DIR / "google_careers_sample.json"
    )
    if not Path(input_file).exists():
        print(f"No sample dataset found at {input_file}; run 'export-sample' first.")
        sys.exit(1)
    summary = run_etl(
        query="sample-dataset",
        source="json",
        input_file=input_file,
        target=args.target,
        dry_run=args.dry_run,
    )
    if args.dry_run:
        print(f"DRY-RUN would_insert={summary['records_to_insert']}")
    else:
        print(
            f"SEED DONE insert={summary.get('records_inserted', 0)} "
            f"duplicates_db={summary.get('duplicates_skipped_db', 0)}"
        )


def cmd_export_sample(args: argparse.Namespace) -> None:
    from src.pipeline import extract_records

    output = args.output or str(RAW_DATA_DIR / "google_careers_sample.json")
    result = extract_records(args.query, limit=args.limit, source="google")
    out = Path(output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(result.records, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )
    print(f"Exported {len(result.records)} records to {out}")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    logger = configure_logging(verbose=getattr(args, "verbose", False))

    if args.version:
        from src import __version__

        print(f"jmip {__version__}")
        return 0

    ensure_directories()

    if args.command == "run":
        cmd_run(args)
    elif args.command == "analyze":
        cmd_analyze(args)
    elif args.command == "migrate":
        cmd_migrate(args)
    elif args.command == "seed":
        cmd_seed(args)
    elif args.command == "export-sample":
        cmd_export_sample(args)
    else:
        parser.print_help()
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())