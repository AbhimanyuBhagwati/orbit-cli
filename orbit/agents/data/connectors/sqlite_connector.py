from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from orbit.agents.data.connectors.base import BaseConnector
from orbit.schemas.data import ConnectionConfig


class SQLiteConnector(BaseConnector):
    """Connector for SQLite databases."""

    def __init__(self, config: ConnectionConfig) -> None:
        super().__init__(config)
        if not config.path:
            msg = "SQLiteConnector requires a 'path' in config"
            raise ValueError(msg)
        self._path = Path(config.path)
        self._conn: sqlite3.Connection | None = None

    @property
    def connector_type(self) -> str:
        return "sqlite"

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(str(self._path))
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def test_connection(self) -> bool:
        if not self._path.exists():
            return False
        try:
            conn = self._get_conn()
            conn.execute("SELECT 1")
            return True
        except Exception:
            return False

    def list_tables(self) -> list[str]:
        conn = self._get_conn()
        cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        return [row[0] for row in cur.fetchall()]

    def get_schema(self, table: str) -> list[tuple[str, str]]:
        conn = self._get_conn()
        cur = conn.execute(f"PRAGMA table_info('{table}')")  # noqa: S608
        return [(row[1], row[2] or "TEXT") for row in cur.fetchall()]

    def get_row_count(self, table: str) -> int:
        conn = self._get_conn()
        cur = conn.execute(f"SELECT COUNT(*) FROM '{table}'")  # noqa: S608
        return cur.fetchone()[0]  # type: ignore[index]

    def get_column_values(self, table: str, column: str, limit: int = 10000) -> list[Any]:
        conn = self._get_conn()
        cur = conn.execute(f"SELECT \"{column}\" FROM '{table}' LIMIT ?", (limit,))  # noqa: S608
        return [row[0] for row in cur.fetchall()]

    def get_size_bytes(self, table: str) -> int | None:
        if self._path.exists():
            return self._path.stat().st_size
        return None

    def sample_rows(self, table: str, n: int = 1000) -> list[dict[str, Any]]:
        conn = self._get_conn()
        cur = conn.execute(f"SELECT * FROM '{table}' LIMIT ?", (n,))  # noqa: S608
        columns = [desc[0] for desc in cur.description or []]
        return [dict(zip(columns, row)) for row in cur.fetchall()]

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None
