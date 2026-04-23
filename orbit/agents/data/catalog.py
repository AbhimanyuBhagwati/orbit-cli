from __future__ import annotations

from orbit.agents.data.connectors.base import BaseConnector
from orbit.schemas.data import CatalogEntry, DataCatalog


def build_catalog(connectors: list[BaseConnector]) -> DataCatalog:
    """Scan all connectors and build a metadata catalog. No LLM, pure schema reads."""
    entries: list[CatalogEntry] = []

    for connector in connectors:
        tables = connector.list_tables()
        for table in tables:
            schema = connector.get_schema(table)
            col_names = [c[0] for c in schema]
            col_types = [c[1] for c in schema]

            try:
                row_count = connector.get_row_count(table)
            except Exception:
                row_count = None

            try:
                size_bytes = connector.get_size_bytes(table)
            except Exception:
                size_bytes = None

            entries.append(
                CatalogEntry(
                    connection_name=connector.config.name,
                    table_name=table,
                    row_count=row_count,
                    column_count=len(col_names),
                    column_names=col_names,
                    column_types=col_types,
                    size_bytes=size_bytes,
                )
            )

    total_tables = len(entries)
    total_columns = sum(e.column_count for e in entries)

    return DataCatalog(
        entries=entries,
        total_tables=total_tables,
        total_columns=total_columns,
    )


def find_similar_columns(catalog: DataCatalog, threshold: float = 0.7) -> list[tuple[list[tuple[str, str]], float, str]]:
    """Find columns with similar names across tables. Fuzzy string matching, no LLM.

    Returns list of ([(table, column), ...], similarity_score, reason).
    """
    results: list[tuple[list[tuple[str, str]], float, str]] = []

    # Collect all (table, column) pairs
    all_columns: list[tuple[str, str]] = []
    for entry in catalog.entries:
        for col_name in entry.column_names:
            all_columns.append((entry.table_name, col_name))

    # Group by normalized name
    normalized: dict[str, list[tuple[str, str]]] = {}
    for table, col in all_columns:
        # Normalize: lowercase, strip underscores/hyphens, remove common suffixes
        norm = col.lower().replace("_", "").replace("-", "").replace(" ", "")
        # Strip common prefixes/suffixes
        for strip in ("id", "num", "number", "code", "key", "name", "address", "date", "time"):
            if norm.endswith(strip) and len(norm) > len(strip):
                base = norm[: -len(strip)]
                if base not in normalized:
                    normalized[base] = []
                normalized[base].append((table, col))
        if norm not in normalized:
            normalized[norm] = []
        normalized[norm].append((table, col))

    # Find groups with columns from multiple tables
    seen: set[frozenset[tuple[str, str]]] = set()
    for norm_name, cols in normalized.items():
        if len(cols) < 2:
            continue
        # Only interesting if from different tables
        tables = set(t for t, _ in cols)
        if len(tables) < 2:
            continue

        key = frozenset(cols)
        if key in seen:
            continue
        seen.add(key)

        results.append((
            cols,
            0.9,  # Exact normalized match = high similarity
            f"Columns share normalized name '{norm_name}'",
        ))

    return results
