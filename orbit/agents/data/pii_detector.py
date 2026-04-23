from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Literal

from orbit.schemas.data import PIIDetection


@dataclass(frozen=True)
class PIIPattern:
    """A regex pattern for detecting PII. Same design as RiskPattern in safety/patterns.py."""

    pattern: re.Pattern[str]
    pii_type: str
    confidence: Literal["high", "medium", "low"]
    description: str


# ── PII Patterns ────────────────────────────────────────────────────────────
# Ordered by specificity: most specific first

_EMAIL = PIIPattern(
    re.compile(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$"),
    "email",
    "high",
    "Email address",
)

_PHONE_US = PIIPattern(
    re.compile(r"^(\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}$"),
    "phone",
    "high",
    "US phone number",
)

_PHONE_INTL = PIIPattern(
    re.compile(r"^\+\d{1,3}[-.\s]?\d{4,14}$"),
    "phone",
    "medium",
    "International phone number",
)

_SSN = PIIPattern(
    re.compile(r"^\d{3}-\d{2}-\d{4}$"),
    "ssn",
    "high",
    "US Social Security Number",
)

_CREDIT_CARD = PIIPattern(
    re.compile(r"^\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}$"),
    "credit_card",
    "high",
    "Credit card number",
)

_IP_ADDRESS = PIIPattern(
    re.compile(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$"),
    "ip_address",
    "medium",
    "IP address",
)

_DATE_OF_BIRTH = PIIPattern(
    re.compile(r"^(0[1-9]|1[0-2])/(0[1-9]|[12]\d|3[01])/(19|20)\d{2}$"),
    "date_of_birth",
    "low",
    "Possible date of birth",
)

_ZIP_CODE = PIIPattern(
    re.compile(r"^\d{5}(-\d{4})?$"),
    "zip_code",
    "low",
    "US ZIP code",
)

_PASSPORT = PIIPattern(
    re.compile(r"^[A-Z]{1,2}\d{6,9}$"),
    "passport",
    "low",
    "Possible passport number",
)

# Column name patterns — detect PII by column name even if values don't match
_NAME_PATTERNS: list[tuple[re.Pattern[str], str, str]] = [
    (re.compile(r"(?i)(^|_)(email|e_?mail)($|_)"), "email", "Column name suggests email"),
    (re.compile(r"(?i)(^|_)(phone|mobile|cell|tel)($|_|_?num)"), "phone", "Column name suggests phone"),
    (re.compile(r"(?i)(^|_)(ssn|social_?sec|sin)($|_)"), "ssn", "Column name suggests SSN"),
    (re.compile(r"(?i)(^|_)(credit_?card|cc_?num|card_?num)($|_)"), "credit_card", "Column name suggests credit card"),
    (re.compile(r"(?i)(^|_)(first_?name|last_?name|full_?name|surname)($|_)"), "name", "Column name suggests name"),
    (re.compile(r"(?i)(^|_)(address|street|city|state|zip|postal)($|_)"), "address", "Column name suggests address"),
    (re.compile(r"(?i)(^|_)(dob|birth_?date|date_?of_?birth)($|_)"), "date_of_birth", "Column name suggests DOB"),
    (re.compile(r"(?i)(^|_)(passport)($|_)"), "passport", "Column name suggests passport"),
    (re.compile(r"(?i)(^|_)(ip_?addr|ip_?address|client_?ip)($|_)"), "ip_address", "Column name suggests IP"),
    (re.compile(r"(?i)(^|_)(salary|income|wage|compensation)($|_)"), "financial", "Column name suggests financial"),
    (re.compile(r"(?i)(^|_)(password|passwd|pwd|secret|token|api_?key)($|_)"), "credential", "Column name suggests credential"),
]

VALUE_PATTERNS: list[PIIPattern] = [
    _SSN,
    _CREDIT_CARD,
    _EMAIL,
    _PHONE_US,
    _PHONE_INTL,
    _IP_ADDRESS,
    _DATE_OF_BIRTH,
    _ZIP_CODE,
    _PASSPORT,
]


def detect_pii_in_column_name(column_name: str) -> PIIDetection | None:
    """Check if a column name suggests PII content. Regex-only, no LLM."""
    for pattern, pii_type, description in _NAME_PATTERNS:
        if pattern.search(column_name):
            return PIIDetection(
                column_name=column_name,
                pii_type=pii_type,
                confidence="medium",
                recommendation=f"Review column — {description.lower()}",
            )
    return None


def detect_pii_in_values(column_name: str, values: list[Any], sample_size: int = 500) -> PIIDetection | None:
    """Scan sample values for PII patterns. Regex-only, no LLM.

    Uses the same deterministic, regex-first approach as safety/classifier.py.
    """
    if not values:
        return None

    # Sample values for performance
    check_values = values[:sample_size]
    str_values = [str(v) for v in check_values if v is not None and str(v).strip()]

    if not str_values:
        return None

    best_match: PIIPattern | None = None
    best_count = 0

    for pii_pattern in VALUE_PATTERNS:
        match_count = sum(1 for v in str_values if pii_pattern.pattern.match(v))
        # Require at least 20% of non-null values to match
        match_pct = match_count / len(str_values)
        if match_pct >= 0.2 and match_count > best_count:
            best_match = pii_pattern
            best_count = match_count

    if best_match is None:
        return None

    return PIIDetection(
        column_name=column_name,
        pii_type=best_match.pii_type,
        confidence=best_match.confidence,
        sample_matches=best_count,
        recommendation=f"Contains {best_match.description} — consider masking or encryption",
    )


def scan_column(column_name: str, values: list[Any]) -> list[PIIDetection]:
    """Full PII scan for a column: checks both name and values."""
    results: list[PIIDetection] = []

    name_hit = detect_pii_in_column_name(column_name)
    if name_hit:
        results.append(name_hit)

    value_hit = detect_pii_in_values(column_name, values)
    if value_hit:
        # If both name and value match, keep the higher-confidence one
        if name_hit and name_hit.pii_type == value_hit.pii_type:
            results = [value_hit]  # Value match is higher confidence
        else:
            results.append(value_hit)

    return results
