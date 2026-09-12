"""Migration of legacy SQLite data into the new normalised schema."""

from src.migration.migrate import migrate_legacy_database, read_legacy_jobs, archive_legacy_database, is_legacy_schema

__all__ = [
    "archive_legacy_database",
    "is_legacy_schema",
    "migrate_legacy_database",
    "read_legacy_jobs",
]