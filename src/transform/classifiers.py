"""Evidence-based job classifiers: seniority, remote work, employment type.

Classification is intentionally conservative. A value of ``Unknown`` is the
default whenever the available evidence is ambiguous, so the pipeline never
guesses.
"""

from __future__ import annotations

import re

SENIORITY_UNKNOWN = "Unknown"
REMOTE_UNKNOWN = "Unknown"
EMPLOYMENT_UNKNOWN = "Unknown"

# --------------------------------------------------------------------------
# Seniority
# --------------------------------------------------------------------------

_SENIORITY_RULES: list[tuple[str, list[str]]] = [
    ("Intern", [r"\bintern(?!\w)", r"\binternship\b"]),
    # Apprenticeships / gReach are early-career programmes at Google.
    ("Entry Level", [r"\bapprenticeship\b", r"\bgReach\b", r"\bnew grad(uate)?\b", r"\bentry[\s-]?level\b"]),
    ("Junior", [r"\bjunior\b", r"\bjr\.?\b"]),
    ("Mid Level", [r"\bmid[\s-]?level\b", r"\bmid\b", r"\bintermediate\b", r"\bLevel II\b", r"\bLevel 2\b"]),
    ("Senior", [r"\bsenior\b", r"\bsr\.?\b", r"\bLevel III\b", r"\bLevel IV\b", r"\bLevel 3\b"]),
    ("Lead", [r"\blead(?!\w)", r"\bleading(?!\w)"]),
    ("Staff", [r"\bstaff\b", r"\bLevel V\b", r"\bLevel 5\b"]),
    ("Principal", [r"\bprincipal\b"]),
    ("Manager", [r"\bmanager(?!\w)", r"\bmgr\.?\b"]),
    ("Director", [r"\bdirector\b", r"\bvp(?: of)?\b", r"\bvice president\b"]),
]

# Seniority indicators lifted out of titles when levels follow a strict
# convention, e.g. "Software Engineer III".
_ROMAN_LEVEL = {1: "Entry Level", 2: "Mid Level", 3: "Senior", 4: "Senior", 5: "Staff"}
_ARABIC_LEVEL = {"1": "Entry Level", "2": "Mid Level", "3": "Senior", "4": "Senior", "5": "Staff"}

_LEVEL_SUFFIX = re.compile(r"\b(?:level|L)?\s*(?P<num>\d{1})$\s*", re.IGNORECASE)
_ROMAN_SUFFIX = re.compile(r"\s(?P<roman>VIII|VII|VI|IV|V|III|II|I)$")
_TITLE_LEVEL = re.compile(r"\b(?:Level|L)\s*(?P<num>\d|V|VI|IV|III|II|I)\b")
_TITLE_WITH_NUM = re.compile(r"\b\w+\s+(?P<num>\d{1,2})$/")

_TITLE_ONLY_WORDS = re.compile(r"^(engineer|analyst|consultant|specialist|associate|scientist|developer)$", re.IGNORECASE)

# Description evidence used only when the title carries no signal. Google
# routinely lists "5 years of experience" as a baseline for many levels, so
# years-of-experience values are intentionally NOT used for classification.
_DESCRIPTION_SENIORITY = re.compile(
    r"\b(?:this is a|we are looking for an?|hiring an?|seeking an?|for an?)\s+"
    r"(?:experienced\s+)?(senior|staff|principal|lead|entry[- ]level|junior)\b",
    re.IGNORECASE,
)


def _level_from_numeric_suffix(title: str) -> str | None:
    m = _TITLE_LEVEL.search(title)
    if m:
        token = m.group("num")
        if token.isdigit():
            return _ARABIC_LEVEL.get(token)
        return _ROMAN_LEVEL.get({"I": 1, "II": 2, "III": 3, "IV": 4, "V": 5, "VI": 5, "VII": 5, "VIII": 5}.get(token))
    m = _ROMAN_SUFFIX.search(title)
    if m:
        return _ROMAN_LEVEL.get({"I": 1, "II": 2, "III": 3, "IV": 4, "V": 5, "VI": 5, "VII": 5, "VIII": 5}.get(m.group("roman")))
    return None


def classify_seniority(title: str, description: str = "") -> str:
    """Classify a job's seniority from title and description evidence."""
    if not title:
        return SENIORITY_UNKNOWN

    # 1. Title keywords, longest patterns first (Manager > Director rules etc).
    for label, patterns in _SENIORITY_RULES:
        for pattern in patterns:
            if re.search(pattern, title, re.IGNORECASE):
                return label

    # 2. Numeric/roman level conventions in the title.
    level = _level_from_numeric_suffix(title)
    if level:
        return level

    # 3. Bare levels, e.g. "Software Engineer II", "Analyst 3".
    m = _LEVEL_SUFFIX.search(title)
    if m and m.group("num").isdigit():
        years = int(m.group("num"))
        return _ARABIC_LEVEL.get(str(years), SENIORITY_UNKNOWN)
    m = _TITLE_WITH_NUM.search(title)
    if m:
        return _ARABIC_LEVEL.get(m.group("num"), SENIORITY_UNKNOWN)

    # 4. Description evidence for explicitly-worded seniority claims.
    if description:
        m = _DESCRIPTION_SENIORITY.search(description)
        if m:
            label = m.group(1).lower()
            mapping = {
                "entry": "Entry Level", "entry-level": "Entry Level",
                "junior": "Junior", "senior": "Senior", "staff": "Staff",
                "principal": "Principal", "lead": "Lead",
            }
            # Normalise "entry level"
            label = "entry-level" if "entry" in label else label
            return mapping.get(label, SENIORITY_UNKNOWN)
    return SENIORITY_UNKNOWN


# --------------------------------------------------------------------------
# Remote work
# --------------------------------------------------------------------------

_REMOTE_RULES: list[tuple[str, list[str]]] = [
    ("Remote", [
        r"\bremote[\s-]?(?:first|eligible|position|role|job|only)?\b",
        r"\bwork from anywhere\b",
        r"\b100%\s*remotely\b",
        r"\btelecommute\b",
    ]),
    ("Hybrid", [
        r"\bhybrid\b",
        r"\bremote +in[\s-]?office\b",
        r"\bsplit (?:between|remote)",
    ]),
    ("Onsite", [
        r"\bon[\s-]?site\b",
        r"\bonsite\b",
        r"\bin[\s-]?office\b",
        r"\bat (?:our|a) [a-z]+ office\b",
        r"\bbased in\b",
    ]),
]


def classify_remote_type(title: str, description: str = "", location_text: str = "") -> str:
    """Classify a job's remote-work arrangement from available evidence."""
    haystack = " ".join([title or "", description or "", location_text or ""])
    for label, patterns in _REMOTE_RULES:
        for pattern in patterns:
            if re.search(pattern, haystack, re.IGNORECASE):
                return label
    return REMOTE_UNKNOWN


# --------------------------------------------------------------------------
# Employment type
# --------------------------------------------------------------------------

_EMPLOYMENT_RULES: list[tuple[str, list[str]]] = [
    ("Internship", [r"\bintern(?!\w)", r"\binternship\b"]),
    ("Part-time", [r"\bpart[\s-]?time\b"]),
    ("Contract", [r"\bcontract\b", r"\bfixed[\s-]?term\b", r"\bfreelance\b", r"\btemp(?:orary)?\b"]),
    ("Temporary", [r"\btemp(?:orary)?\b"]),
    ("Full-time", [r"\bfull[\s-]?time\b"]),
]


def classify_employment_type(title: str, description: str = "") -> str:
    """Classify a job's employment type from title and description evidence."""
    haystack = " ".join([title or "", description or ""])
    # Look for explicit markers only; default to Unknown when absent.
    if re.search(r"\bpart[\s-]?time\b", haystack, re.IGNORECASE):
        return "Part-time"
    if re.search(r"\bintern(?:ship)?\b", haystack, re.IGNORECASE):
        return "Internship"
    if re.search(r"\b(?:fixed[\s-]?term|contract|temp(?:orary)?|freelance)\b", haystack, re.IGNORECASE):
        return "Contract"
    if re.search(r"\bfull[\s-]?time\b", haystack, re.IGNORECASE):
        return "Full-time"
    return EMPLOYMENT_UNKNOWN