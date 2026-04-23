from __future__ import annotations

from orbit.schemas.data import CatalogEntry, ColumnProfile, DataCatalog, TableProfile


def _format_size(size_bytes: int | None) -> str:
    """Human-readable file size."""
    if size_bytes is None:
        return "unknown"
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024  # type: ignore[assignment]
    return f"{size_bytes:.1f} PB"


def compress_column_for_llm(col: ColumnProfile) -> str:
    """Compress a column profile into a minimal string for LLM context.

    Designed to fit even in a 7B model's context window.
    ~50-80 tokens per column.
    """
    parts = [f"'{col.name}': {col.dtype}"]

    if col.null_pct > 0:
        parts.append(f"{col.null_pct}% null")

    parts.append(f"{col.unique_count} unique")

    if col.mean_value is not None:
        parts.append(f"mean={col.mean_value}")
    if col.min_value is not None and col.max_value is not None:
        parts.append(f"range=[{col.min_value}, {col.max_value}]")

    if col.top_values:
        top3 = ", ".join(f"{v}({c})" for v, c in col.top_values[:3])
        parts.append(f"top: {top3}")

    if col.inferred_semantic:
        parts.append(f"[{col.inferred_semantic}]")

    return " | ".join(parts)


def compress_table_for_llm(profile: TableProfile, max_columns: int = 20) -> str:
    """Compress a table profile for LLM consumption.

    For 7B models: keeps only top issues and first N columns.
    For larger models: can handle more.
    """
    lines = [
        f"TABLE: {profile.table_name} ({profile.row_count} rows, {profile.column_count} cols, {_format_size(profile.size_bytes)})",
        f"Quality: {profile.quality_score}/100",
    ]

    # Columns (limited)
    cols_to_show = profile.columns[:max_columns]
    for col in cols_to_show:
        lines.append(f"  {compress_column_for_llm(col)}")

    if len(profile.columns) > max_columns:
        lines.append(f"  ... and {len(profile.columns) - max_columns} more columns")

    # Issues (top 10)
    if profile.issues:
        lines.append("ISSUES:")
        for issue in profile.issues[:10]:
            lines.append(f"  [{issue.severity}] {issue.description}")

    return "\n".join(lines)


def compress_catalog_for_llm(catalog: DataCatalog, max_tables: int = 10) -> str:
    """Compress entire catalog for LLM. Fits in ~2k tokens even for large databases."""
    lines = [
        f"CATALOG: {catalog.total_tables} tables, {catalog.total_columns} total columns",
        "",
    ]

    for entry in catalog.entries[:max_tables]:
        cols_preview = ", ".join(entry.column_names[:10])
        if len(entry.column_names) > 10:
            cols_preview += f", ... +{len(entry.column_names) - 10} more"
        size = _format_size(entry.size_bytes)
        rows = f"{entry.row_count} rows" if entry.row_count is not None else "? rows"
        lines.append(f"  {entry.connection_name}.{entry.table_name}: {entry.column_count} cols, {rows}, {size}")
        lines.append(f"    cols: {cols_preview}")

    if len(catalog.entries) > max_tables:
        lines.append(f"  ... and {len(catalog.entries) - max_tables} more tables")

    return "\n".join(lines)


def estimate_llm_tokens(text: str) -> int:
    """Rough token estimate (~4 chars per token for English)."""
    return len(text) // 4


def pick_strategy(metadata_text: str, model_context_window: int) -> str:
    """Pick LLM interaction strategy based on available context.

    Returns: 'full', 'chunked', or 'micro'
    """
    tokens = estimate_llm_tokens(metadata_text)
    usable = int(model_context_window * 0.7)  # Leave 30% for response

    if tokens < usable:
        return "full"
    elif tokens < model_context_window * 5:
        return "chunked"
    else:
        return "micro"


def build_micro_questions(profile: TableProfile) -> list[str]:
    """Build tiny, focused questions for 7B models. One question per issue.

    Each question is <200 tokens so even a 4k context model handles it.
    """
    questions: list[str] = []

    for issue in profile.issues[:10]:
        if issue.category == "pii":
            questions.append(
                f"Column '{issue.column}' in table '{profile.table_name}' "
                f"contains {issue.description}. "
                "What should we do about this? Answer in 1-2 sentences."
            )
        elif issue.category == "nulls":
            questions.append(
                f"Column '{issue.column}' in '{profile.table_name}' is {issue.description}. "
                "Should we drop it, impute, or keep? Answer in 1 sentence."
            )
        elif issue.category == "outliers":
            questions.append(
                f"{issue.description}. "
                "Are these likely real values or data errors? Answer in 1 sentence."
            )

    # Column meaning questions for ambiguous names
    for col in profile.columns:
        if col.name and len(col.name) <= 5 and col.name.lower() not in ("id", "name", "date", "type", "code"):
            sample = ", ".join(col.sample_values[:3]) if col.sample_values else "N/A"
            questions.append(
                f"Column '{col.name}' in '{profile.table_name}': "
                f"type={col.dtype}, samples=[{sample}]. "
                "What does this column likely contain? Answer in 1 sentence."
            )

    return questions


def generate_summary_prompt(catalog_text: str) -> str:
    """Generate a prompt for LLM to summarize the catalog."""
    return (
        "You are a data analyst assistant. Below is a catalog of tables and columns.\n"
        "Provide a brief summary of:\n"
        "1. What this data appears to be about\n"
        "2. Key relationships between tables\n"
        "3. Top 3 data quality concerns\n"
        "4. Suggested next steps for the user\n\n"
        "Be concise — max 10 sentences.\n\n"
        f"{catalog_text}"
    )
