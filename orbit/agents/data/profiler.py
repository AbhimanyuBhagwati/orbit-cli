from __future__ import annotations

from typing import Any

from orbit.agents.data.connectors.base import BaseConnector
from orbit.agents.data.pii_detector import scan_column
from orbit.schemas.data import ColumnProfile, DataIssue, TableProfile


def _safe_str(value: Any) -> str:
    """Convert a value to string safely."""
    if value is None:
        return ""
    return str(value)


def _compute_column_profile(
    column_name: str,
    dtype: str,
    values: list[Any],
    total_rows: int,
) -> ColumnProfile:
    """Compute statistics for a single column. Pure Python/math, no LLM."""
    null_count = sum(1 for v in values if v is None)
    non_null = [v for v in values if v is not None]
    null_pct = round((null_count / total_rows * 100) if total_rows > 0 else 0, 2)

    unique_values = set(_safe_str(v) for v in non_null)
    unique_count = len(unique_values)
    unique_pct = round((unique_count / len(non_null) * 100) if non_null else 0, 2)

    # Min/max
    min_value = None
    max_value = None
    mean_value = None
    median_value = None
    std_value = None

    # Numeric stats
    numeric_values: list[float] = []
    for v in non_null:
        try:
            numeric_values.append(float(v))
        except (ValueError, TypeError):
            pass

    is_numeric = len(numeric_values) > len(non_null) * 0.8  # 80% numeric threshold

    if is_numeric and numeric_values:
        numeric_values.sort()
        min_value = _safe_str(numeric_values[0])
        max_value = _safe_str(numeric_values[-1])
        mean_value = round(sum(numeric_values) / len(numeric_values), 4)
        mid = len(numeric_values) // 2
        median_value = (
            numeric_values[mid]
            if len(numeric_values) % 2 == 1
            else round((numeric_values[mid - 1] + numeric_values[mid]) / 2, 4)
        )
        if len(numeric_values) > 1:
            mean_val = sum(numeric_values) / len(numeric_values)
            variance = sum((x - mean_val) ** 2 for x in numeric_values) / (len(numeric_values) - 1)
            std_value = round(variance**0.5, 4)
    elif non_null:
        str_values = sorted(_safe_str(v) for v in non_null)
        min_value = str_values[0][:100]
        max_value = str_values[-1][:100]

    # Top values (frequency)
    freq: dict[str, int] = {}
    for v in non_null:
        s = _safe_str(v)[:200]
        freq[s] = freq.get(s, 0) + 1
    top_values = sorted(freq.items(), key=lambda x: x[1], reverse=True)[:5]

    # Sample values
    sample_values = [_safe_str(v)[:200] for v in non_null[:5]]

    return ColumnProfile(
        name=column_name,
        dtype=dtype,
        total_count=total_rows,
        null_count=null_count,
        null_pct=null_pct,
        unique_count=unique_count,
        unique_pct=unique_pct,
        min_value=min_value,
        max_value=max_value,
        mean_value=mean_value,
        median_value=median_value,
        std_value=std_value,
        top_values=top_values,
        sample_values=sample_values,
    )


def _detect_issues(columns: list[ColumnProfile], total_rows: int) -> list[DataIssue]:
    """Detect data quality issues. Deterministic rules, no LLM."""
    issues: list[DataIssue] = []

    for col in columns:
        # High null percentage
        if col.null_pct > 50:
            issues.append(
                DataIssue(
                    severity="critical",
                    category="nulls",
                    column=col.name,
                    description=f"Column '{col.name}' is {col.null_pct}% null",
                    suggestion="Consider dropping this column or investigating why it's mostly empty",
                )
            )
        elif col.null_pct > 10:
            issues.append(
                DataIssue(
                    severity="warning",
                    category="nulls",
                    column=col.name,
                    description=f"Column '{col.name}' has {col.null_pct}% nulls ({col.null_count} rows)",
                    suggestion="Impute missing values or filter nulls for analysis",
                )
            )

        # Single value (zero variance)
        if col.unique_count == 1 and col.total_count > 10:
            issues.append(
                DataIssue(
                    severity="warning",
                    category="variance",
                    column=col.name,
                    description=f"Column '{col.name}' has only 1 unique value — provides no information",
                    suggestion="Consider dropping this column",
                )
            )

        # All unique (possible ID column)
        if col.unique_pct > 99 and col.total_count > 100 and col.dtype not in ("Int64", "int", "integer"):
            issues.append(
                DataIssue(
                    severity="info",
                    category="cardinality",
                    column=col.name,
                    description=f"Column '{col.name}' has {col.unique_pct}% unique values — may be an ID column",
                    suggestion="Verify if this is an identifier; avoid using in aggregations",
                )
            )

        # Numeric outliers (using IQR)
        if col.mean_value is not None and col.std_value is not None and col.std_value > 0:
            if col.min_value and col.max_value:
                try:
                    min_v = float(col.min_value)
                    max_v = float(col.max_value)
                    spread = max_v - min_v
                    if col.std_value > 0 and spread > col.std_value * 10:
                        issues.append(
                            DataIssue(
                                severity="warning",
                                category="outliers",
                                column=col.name,
                                description=(
                                    f"Column '{col.name}' has extreme range "
                                    f"(min={col.min_value}, max={col.max_value}, std={col.std_value})"
                                ),
                                suggestion="Check for outliers or data entry errors",
                            )
                        )
                except (ValueError, TypeError):
                    pass

        # Negative values in likely-positive columns
        if col.min_value is not None and col.mean_value is not None:
            try:
                min_v = float(col.min_value)
                if min_v < 0 and col.mean_value > 0:
                    name_lower = col.name.lower()
                    positive_hints = ("count", "qty", "quantity", "amount", "price", "age", "size", "length", "weight")
                    if any(h in name_lower for h in positive_hints):
                        issues.append(
                            DataIssue(
                                severity="warning",
                                category="values",
                                column=col.name,
                                description=f"Column '{col.name}' has negative values (min={col.min_value}) but name suggests positive",
                                suggestion="Verify if negative values are intentional (refunds, adjustments, etc.)",
                            )
                        )
            except (ValueError, TypeError):
                pass

    # Global issues
    if total_rows == 0:
        issues.append(
            DataIssue(
                severity="critical",
                category="empty",
                column=None,
                description="Table has 0 rows",
                suggestion="Check if data was loaded correctly",
            )
        )

    return issues


def _compute_quality_score(columns: list[ColumnProfile], issues: list[DataIssue]) -> float:
    """Compute a data quality score 0-100. Deterministic formula."""
    if not columns:
        return 0.0

    score = 100.0

    # Deduct for issues
    for issue in issues:
        if issue.severity == "critical":
            score -= 15
        elif issue.severity == "warning":
            score -= 5
        elif issue.severity == "info":
            score -= 1

    # Deduct for average null percentage
    avg_null_pct = sum(c.null_pct for c in columns) / len(columns)
    score -= avg_null_pct * 0.3

    return max(0.0, min(100.0, round(score, 1)))


def profile_table(connector: BaseConnector, table: str, sample_limit: int = 10000) -> TableProfile:
    """Profile a table end-to-end. Compute-heavy work in Python, zero LLM calls.

    Args:
        connector: Data source connector.
        table: Table or file name.
        sample_limit: Max rows to sample per column for profiling.
    """
    schema = connector.get_schema(table)
    row_count = connector.get_row_count(table)
    size_bytes = connector.get_size_bytes(table)

    columns: list[ColumnProfile] = []
    all_pii = []

    for col_name, col_type in schema:
        values = connector.get_column_values(table, col_name, limit=sample_limit)
        profile = _compute_column_profile(col_name, col_type, values, total_rows=min(row_count, sample_limit))
        columns.append(profile)

        # PII detection (regex-based)
        pii_hits = scan_column(col_name, values[:500])
        all_pii.extend(pii_hits)

    issues = _detect_issues(columns, row_count)

    # Add PII as issues
    for pii in all_pii:
        issues.append(
            DataIssue(
                severity="critical" if pii.confidence == "high" else "warning",
                category="pii",
                column=pii.column_name,
                description=f"PII detected: {pii.pii_type} ({pii.confidence} confidence)",
                suggestion=pii.recommendation,
            )
        )

    quality_score = _compute_quality_score(columns, issues)

    return TableProfile(
        source_name=connector.config.name,
        table_name=table,
        row_count=row_count,
        column_count=len(columns),
        size_bytes=size_bytes,
        columns=columns,
        pii_detections=all_pii,
        issues=issues,
        quality_score=quality_score,
    )
