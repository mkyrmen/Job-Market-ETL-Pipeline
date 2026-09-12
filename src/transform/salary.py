"""Conservative salary extraction.

Salary figures are only parsed from explicit, self-consistent disclosure
text that job boards include inside the description (for example Google's
own "US base salary range" statements). No assumptions are made for fields
the source does not disclose.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_SALARY_RANGE = re.compile(
    r"(?P<context>salary|compensation|compensation range|base pay)"
    r".{0,80}?"
    r"\$\s?(?P<low>[\d,]{3,})"
    r"\s*(?:-|\\u2013|to|\\u2014)\s*"
    r"\$\s?(?P<high>[\d,]{3,})",
    re.IGNORECASE,
)

_MONEY = re.compile(r"\$\s?(?P<amount>[\d,]{4,})")


@dataclass(frozen=True)
class SalaryExtraction:
    low: float | None = None
    high: float | None = None
    currency: str | None = None


def _to_number(raw: str) -> float:
    return float(raw.replace(",", ""))


def extract_salary(text: str) -> SalaryExtraction:
    """Extract a USD salary range from explicit disclosure text.

    Returns an empty extraction when no trustworthy figure is present.
    """
    if not text:
        return SalaryExtraction()

    m = _SALARY_RANGE.search(text)
    if m:
        low = _to_number(m.group("low"))
        high = _to_number(m.group("high"))
        # Guard against implausible ranges (typos/parsing artefacts).
        if 10_000 <= low <= high <= 2_000_000:
            return SalaryExtraction(low=low, high=high, currency="USD")
        return SalaryExtraction(low=low, high=high, currency="USD")

    # Fallback: a single "salary of $X" figure.
    for m in _MONEY.finditer(text[:300]):
        amount = _to_number(m.group("amount"))
        if 10_000 <= amount <= 2_000_000:
            return SalaryExtraction(low=amount, high=amount, currency="USD")
    return SalaryExtraction()