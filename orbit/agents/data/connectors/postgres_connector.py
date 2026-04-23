from __future__ import annotations

from typing import Any

from orbit.agents.data.connectors.base import BaseConnector
from orbit.schemas.data import ConnectionConfig


def _require_psycopg() -> Any:
    try:
        import psycopg2

        return psycopg2
    except ImportError as e:
        raise ImportError("Install psycopg2: pip install psycopg2-binary") from e


class PostgresConnector(BaseConnector):
    """Connector for PostgreSQL databases."""

    def __init__(self, config: ConnectionConfig) -> None:
        super().__init__(config)
        self._psycopg2 = _require_psycopg()
        self._conn: Any = None
        self._schema = config.extra.get("schema", "public")

    @property
    def connector_type(self) -> str:
        return "postgres"

    def _get_conn(self) -> Any:
        if self._conn is None or self._conn.closed:
            self._conn = self._psycopg2.connect(
                host=self.config.host or "localhost",
                port=self.config.port or 5432,
                database=self.config.database or "postgres",
                user=self.config.username or "postgres",
                password=self.config.password or "",
            )
        return self._conn

    def test_connection(self) -> bool:
        try:
            conn = self._get_conn()
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
            return True
        except Exception:
            return False

    def list_tables(self) -> list[str]:
        conn = self._get_conn()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = %s ORDER BY table_name",
                (self._schema,),
            )
            return [row[0] for row in cur.fetchall()]

    def get_schema(self, table: str) -> list[tuple[str, str]]:
        conn = self._get_conn()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT column_name, data_type FROM information_schema.columns "
                "WHERE table_schema = %s AND table_name = %s ORDER BY ordinal_position",
                (self._schema, table),
            )
            return [(row[0], row[1]) for row in cur.fetchall()]

    def get_row_count(self, table: str) -> int:
        conn = self._get_conn()
        with conn.cursor() as cur:
            # Use estimate for large tables, exact for small
            cur.execute(
                "SELECT reltuples::bigint FROM pg_class WHERE relname = %s",
                (table,),
            )
            row = cur.fetchone()
            estimate = row[0] if row else 0
            # If estimate is small or negative (never analyzed), do exact count
            if estimate < 10000:
                cur.execute(f'SELECT COUNT(*) FROM "{self._schema}"."{table}"')  # noqa: S608
                return cur.fetchone()[0]  # type: ignore[index]
            return max(0, estimate)

    def get_column_values(self, table: str, column: str, limit: int = 10000) -> list[Any]:
        conn = self._get_conn()
        with conn.cursor() as cur:
            cur.execute(
                f'SELECT "{column}" FROM "{self._schema}"."{table}" LIMIT %s',  # noqa: S608
                (limit,),
            )
            return [row[0] for row in cur.fetchall()]

    def get_size_bytes(self, table: str) -> int | None:
        conn = self._get_conn()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT pg_total_relation_size(quote_ident(%s)::regclass)",
                (table,),
            )
            row = cur.fetchone()
            return row[0] if row else None

    def sample_rows(self, table: str, n: int = 1000) -> list[dict[str, Any]]:
        conn = self._get_conn()
        with conn.cursor() as cur:
            cur.execute(f'SELECT * FROM "{self._schema}"."{table}" LIMIT %s', (n,))  # noqa: S608
            columns = [desc[0] for desc in cur.description or []]
            return [dict(zip(columns, row)) for row in cur.fetchall()]

    def close(self) -> None:
        if self._conn is not None and not self._conn.closed:
            self._conn.close()
            self._conn = None
