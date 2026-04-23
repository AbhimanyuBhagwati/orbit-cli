from __future__ import annotations

from orbit.agents.data.catalog import build_catalog, find_similar_columns
from orbit.agents.data.connections import list_connections, load_connection
from orbit.agents.data.connectors.base import BaseConnector
from orbit.agents.data.connectors.factory import create_connector
from orbit.agents.data.profiler import profile_table
from orbit.schemas.data import ConnectionConfig, DataCatalog, TableProfile


def connect(config: ConnectionConfig) -> BaseConnector:
    """Create and test a connector."""
    connector = create_connector(config)
    if not connector.test_connection():
        msg = f"Failed to connect to {config.name} ({config.connector_type})"
        raise ConnectionError(msg)
    return connector


def scan_all() -> DataCatalog:
    """Scan all saved connections and build a catalog."""
    names = list_connections()
    connectors: list[BaseConnector] = []

    for name in names:
        config = load_connection(name)
        if config is None:
            continue
        try:
            conn = create_connector(config)
            if conn.test_connection():
                connectors.append(conn)
        except Exception:
            continue

    catalog = build_catalog(connectors)

    # Clean up
    for conn in connectors:
        conn.close()

    return catalog


def profile(connection_name: str, table: str, sample_limit: int = 10000) -> TableProfile:
    """Profile a specific table from a saved connection."""
    config = load_connection(connection_name)
    if config is None:
        msg = f"Connection '{connection_name}' not found"
        raise ValueError(msg)

    connector = create_connector(config)
    if not connector.test_connection():
        msg = f"Cannot connect to '{connection_name}'"
        raise ConnectionError(msg)

    try:
        return profile_table(connector, table, sample_limit=sample_limit)
    finally:
        connector.close()


def profile_file(path: str, sample_limit: int = 10000) -> TableProfile:
    """Profile a file directly without saving a connection."""
    from pathlib import Path

    file_path = Path(path)
    suffix = file_path.suffix.lower().lstrip(".")
    if suffix not in ("csv", "parquet", "json"):
        msg = f"Unsupported file type: {suffix}. Use csv, parquet, or json."
        raise ValueError(msg)

    config = ConnectionConfig(
        name=file_path.stem,
        connector_type=suffix,  # type: ignore[arg-type]
        path=str(file_path),
    )
    connector = create_connector(config)
    if not connector.test_connection():
        msg = f"File not found: {path}"
        raise FileNotFoundError(msg)

    try:
        tables = connector.list_tables()
        if not tables:
            msg = f"No data found in {path}"
            raise ValueError(msg)
        return profile_table(connector, tables[0], sample_limit=sample_limit)
    finally:
        connector.close()


def find_duplicates(catalog: DataCatalog) -> list[tuple[list[tuple[str, str]], float, str]]:
    """Find similar/duplicate columns across all tables."""
    return find_similar_columns(catalog)
