"""Extraction base types and result model."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class ExtractionResult:
    """Outcome of an extraction run against a single source."""

    source: str
    query: str
    records: list[dict] = field(default_factory=list)
    pages_fetched: int = 0
    warnings: list[str] = field(default_factory=list)


class Extractor(Protocol):
    """Protocol for concrete extractors.

    An extractor returns a list of *raw record* dictionaries in the schema
    consumed by ``RawRecord`` (see ``src/models.py``).
    """

    def extract(self, query: str, limit: int | None = None) -> ExtractionResult:
        ...