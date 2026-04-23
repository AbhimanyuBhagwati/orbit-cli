from __future__ import annotations

from orbit.agents.data.connectors.base import BaseConnector
from orbit.schemas.data import ConnectionConfig


def create_connector(config: ConnectionConfig) -> BaseConnector:
    """Factory: create a connector from config."""
    if config.connector_type in ("csv", "parquet", "json"):
        from orbit.agents.data.connectors.file_connector import FileConnector

        return FileConnector(config)

    if config.connector_type == "sqlite":
        from orbit.agents.data.connectors.sqlite_connector import SQLiteConnector

        return SQLiteConnector(config)

    if config.connector_type == "postgres":
        from orbit.agents.data.connectors.postgres_connector import PostgresConnector

        return PostgresConnector(config)

    msg = f"Unsupported connector type: {config.connector_type}"
    raise ValueError(msg)
