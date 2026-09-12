"""Validation layer between extraction and transformation.

Raw records are coerced onto the ``RawRecord`` schema; malformed rows are
reported and dropped rather than silently passing through.
"""

from __future__ import annotations

import logging
from typing import Any

from pydantic import ValidationError

from src.models import RawRecord

logger = logging.getLogger(__name__)


def validate_raw_records(
    records: list[dict[str, Any]],
) -> tuple[list[RawRecord], list[tuple[dict[str, Any], str]]]:
    """Validate a batch of extracted records.

    Returns ``(valid_records, errors)`` where each error is a
    ``(original_record, reason)`` pair.
    """
    valid: list[RawRecord] = []
    errors: list[tuple[dict[str, Any], str]] = []

    for record in records:
        if not isinstance(record, dict):
            errors.append((record, "record is not a mapping"))
            continue
        try:
            raw = RawRecord.model_validate(record)
        except ValidationError as exc:
            details = "; ".join(
                f"{'.'.join(str(p) for p in err['loc'])}: {err['msg']}"
                for err in exc.errors()
            )
            errors.append((record, details))
            continue

        if not (raw.title or "").strip():
            errors.append((record, "missing title"))
            continue
        valid.append(raw)

    logger.info(
        "Validation: %d valid, %d invalid records",
        len(valid), len(errors),
    )
    return valid, errors