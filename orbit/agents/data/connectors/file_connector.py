from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from orbit.agents.data.connectors.base import BaseConnector
from orbit.schemas.data import ConnectionConfig


def _require_polars() -> Any:
    try:
        import polars as pl

        return pl
    except ImportError as e:
        raise ImportError("Install polars: pip install polars") from e


class FileConnector(BaseConnector):
    """Connector for CSV, Parquet, and JSON files."""

    def __init__(self, config: ConnectionConfig) -> None:
        super().__init__(config)
        if not config.path:
            msg = "FileConnector requires a 'path' in config"
            raise ValueError(msg)
        self._path = Path(config.path)
        self._pl = _require_polars()
        self._frames: dict[str, Any] = {}

    @property
    def connector_type(self) -> str:
        return self.config.connector_type

    def _load(self, table: str) -> Any:
        """Lazy-load a file into a polars DataFrame."""
        if table in self._frames:
            return self._frames[table]

        path = self._resolve_path(table)
        suffix = path.suffix.lower()

        if suffix == ".csv":
            df = self._pl.read_csv(path, infer_schema_length=10000, ignore_errors=True)
        elif suffix == ".parquet":
            df = self._pl.read_parquet(path)
        elif suffix == ".json":
            raw = json.loads(path.read_text())
            if isinstance(raw, list):
                df = self._pl.DataFrame(raw)
            elif isinstance(raw, dict) and any(isinstance(v, list) for v in raw.values()):
                # Find the first list value and use that
                for v in raw.values():
                    if isinstance(v, list):
                        df = self._pl.DataFrame(v)
                        break
                else:
                    df = self._pl.DataFrame([raw])
            else:
                df = self._pl.DataFrame([raw])
        else:
            msg = f"Unsupported file format: {suffix}"
            raise ValueError(msg)

        self._frames[table] = df
        return df

    def _resolve_path(self, table: str) -> Path:
        """Resolve table name to file path."""
        # If path is a directory, table is a filename within it
        if self._path.is_dir():
            return self._path / table
        # If path is a file, table should match the filename
        return self._path

    def test_connection(self) -> bool:
        return self._path.exists()

    def list_tables(self) -> list[str]:
        if self._path.is_file():
            return [self._path.name]

        if self._path.is_dir():
            extensions = {".csv", ".parquet", ".json"}
            return sorted(f.name for f in self._path.iterdir() if f.suffix.lower() in extensions and f.is_file())

        return []

    def get_schema(self, table: str) -> list[tuple[str, str]]:
        df = self._load(table)
        return [(name, str(dtype)) for name, dtype in zip(df.columns, df.dtypes)]

    def get_row_count(self, table: str) -> int:
        df = self._load(table)
        return len(df)

    def get_column_values(self, table: str, column: str, limit: int = 10000) -> list[Any]:
        df = self._load(table)
        series = df[column].head(limit)
        return series.to_list()

    def get_size_bytes(self, table: str) -> int | None:
        path = self._resolve_path(table)
        if path.exists():
            return path.stat().st_size
        return None

    def sample_rows(self, table: str, n: int = 1000) -> list[dict[str, Any]]:
        df = self._load(table)
        sample = df.head(n)
        return sample.to_dicts()
