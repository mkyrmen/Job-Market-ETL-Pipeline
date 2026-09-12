"""Application configuration.

All configuration is environment driven (see ``.env.example``). Paths are
resolved relative to the repository root so the ETL never depends on
hard-coded absolute locations.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Repository root: <repo>/src/config.py -> parent.parent is the repo root.
REPO_ROOT = Path(__file__).resolve().parent.parent

DATA_DIR = REPO_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"

DEFAULT_SQLITE_PATH = DATA_DIR / "jobs_database.db"


class Settings(BaseSettings):
    """Runtime settings for the ETL pipeline."""

    model_config = SettingsConfigDict(
        env_file=REPO_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Logging
    log_level: str = "INFO"

    # ETL defaults
    etl_limit: int = 100
    request_timeout_seconds: float = 25.0
    max_http_retries: int = 3
    user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    )

    # Persistence
    database_path: Path = DEFAULT_SQLITE_PATH
    supabase_url: str | None = None
    supabase_anon_key: str | None = None
    supabase_service_role_key: str | None = None
    database_url: str | None = None

    @property
    def supabase_configured(self) -> bool:
        """True when production Supabase credentials are available."""
        return bool(self.supabase_url and self.supabase_service_role_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()


def ensure_directories() -> None:
    """Create the local data directories if they do not exist."""
    for path in (DATA_DIR, RAW_DATA_DIR, PROCESSED_DATA_DIR, REPO_ROOT / "logs"):
        path.mkdir(parents=True, exist_ok=True)
    if not os.environ.get("ETL_NO_DB_DIR"):
        DEFAULT_SQLITE_PATH.parent.mkdir(parents=True, exist_ok=True)