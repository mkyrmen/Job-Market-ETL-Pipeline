"""Load-layer contract and shared outcome types."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from src.models import JobRecord


@dataclass
class LoadResult:
    """Outcome of persisting a batch of job records."""

    inserted: int = 0
    duplicates_skipped: int = 0
    errors: int = 0


class Loader(Protocol):
    """Protocol implemented by persistence backends."""

    def upsert_jobs(self, jobs: list[JobRecord]) -> LoadResult:
        """Persist job records, skipping duplicates; return counts."""
        ...

    def close(self) -> None:
        """Release backend resources."""
        ...