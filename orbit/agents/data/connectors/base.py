from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from orbit.schemas.data import ConnectionConfig


class BaseConnector(ABC):
    """Abstract base for data source connectors."""

    def __init__(self, config: ConnectionConfig) -> None:
        self.config = config

    @property
    @abstractmethod
    def connector_type(self) -> str: ...

    @abstractmethod
    def test_connection(self) -> bool:
        """Test if the connection is valid."""
        ...

    @abstractmethod
    def list_tables(self) -> list[str]:
        """List all tables/files in this source."""
        ...

    @abstractmethod
    def get_schema(self, table: str) -> list[tuple[str, str]]:
        """Return list of (column_name, column_type) for a table."""
        ...

    @abstractmethod
    def get_row_count(self, table: str) -> int:
        """Return row count for a table."""
        ...

    @abstractmethod
    def sample_rows(self, table: str, n: int = 1000) -> list[dict[str, Any]]:
        """Return n sample rows as list of dicts."""
        ...

    @abstractmethod
    def get_column_values(self, table: str, column: str, limit: int = 10000) -> list[Any]:
        """Return values for a specific column (for profiling)."""
        ...

    @abstractmethod
    def get_size_bytes(self, table: str) -> int | None:
        """Return size on disk if available."""
        ...

    def close(self) -> None:
        """Clean up resources. Override if needed."""
