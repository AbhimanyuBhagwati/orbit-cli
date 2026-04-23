from __future__ import annotations

import json
import sqlite3
import tempfile
from pathlib import Path

import pytest

from orbit.agents.data.connectors.factory import create_connector
from orbit.agents.data.connectors.file_connector import FileConnector
from orbit.agents.data.connectors.sqlite_connector import SQLiteConnector
from orbit.schemas.data import ConnectionConfig


class TestFileConnectorCSV:
    @pytest.fixture()
    def csv_file(self, tmp_path: Path) -> Path:
        content = "a,b,c\n1,hello,3.14\n2,world,2.72\n3,foo,1.41\n"
        p = tmp_path / "test.csv"
        p.write_text(content)
        return p

    def test_test_connection(self, csv_file: Path) -> None:
        config = ConnectionConfig(name="test", connector_type="csv", path=str(csv_file))
        conn = FileConnector(config)
        assert conn.test_connection() is True

    def test_test_connection_missing(self, tmp_path: Path) -> None:
        config = ConnectionConfig(name="test", connector_type="csv", path=str(tmp_path / "missing.csv"))
        conn = FileConnector(config)
        assert conn.test_connection() is False

    def test_list_tables_single_file(self, csv_file: Path) -> None:
        config = ConnectionConfig(name="test", connector_type="csv", path=str(csv_file))
        conn = FileConnector(config)
        tables = conn.list_tables()
        assert tables == ["test.csv"]

    def test_list_tables_directory(self, tmp_path: Path) -> None:
        (tmp_path / "a.csv").write_text("x\n1\n")
        (tmp_path / "b.parquet").touch()  # Won't be readable but will be listed
        (tmp_path / "c.txt").write_text("ignore")
        config = ConnectionConfig(name="test", connector_type="csv", path=str(tmp_path))
        conn = FileConnector(config)
        tables = conn.list_tables()
        assert "a.csv" in tables
        assert "c.txt" not in tables

    def test_get_schema(self, csv_file: Path) -> None:
        config = ConnectionConfig(name="test", connector_type="csv", path=str(csv_file))
        conn = FileConnector(config)
        schema = conn.get_schema("test.csv")
        col_names = [c[0] for c in schema]
        assert "a" in col_names
        assert "b" in col_names
        assert "c" in col_names

    def test_get_row_count(self, csv_file: Path) -> None:
        config = ConnectionConfig(name="test", connector_type="csv", path=str(csv_file))
        conn = FileConnector(config)
        assert conn.get_row_count("test.csv") == 3  # noqa: PLR2004

    def test_get_column_values(self, csv_file: Path) -> None:
        config = ConnectionConfig(name="test", connector_type="csv", path=str(csv_file))
        conn = FileConnector(config)
        values = conn.get_column_values("test.csv", "b")
        assert values == ["hello", "world", "foo"]

    def test_sample_rows(self, csv_file: Path) -> None:
        config = ConnectionConfig(name="test", connector_type="csv", path=str(csv_file))
        conn = FileConnector(config)
        rows = conn.sample_rows("test.csv", n=2)
        assert len(rows) == 2  # noqa: PLR2004
        assert "a" in rows[0]

    def test_get_size(self, csv_file: Path) -> None:
        config = ConnectionConfig(name="test", connector_type="csv", path=str(csv_file))
        conn = FileConnector(config)
        size = conn.get_size_bytes("test.csv")
        assert size is not None
        assert size > 0


class TestFileConnectorJSON:
    @pytest.fixture()
    def json_file(self, tmp_path: Path) -> Path:
        data = [{"x": 1, "y": "a"}, {"x": 2, "y": "b"}]
        p = tmp_path / "data.json"
        p.write_text(json.dumps(data))
        return p

    def test_json_schema(self, json_file: Path) -> None:
        config = ConnectionConfig(name="test", connector_type="json", path=str(json_file))
        conn = FileConnector(config)
        schema = conn.get_schema("data.json")
        assert len(schema) == 2  # noqa: PLR2004

    def test_json_row_count(self, json_file: Path) -> None:
        config = ConnectionConfig(name="test", connector_type="json", path=str(json_file))
        conn = FileConnector(config)
        assert conn.get_row_count("data.json") == 2  # noqa: PLR2004


class TestSQLiteConnector:
    @pytest.fixture()
    def sqlite_db(self, tmp_path: Path) -> Path:
        db_path = tmp_path / "test.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT, email TEXT, age INTEGER)")
        conn.execute("INSERT INTO users VALUES (1, 'Alice', 'alice@test.com', 30)")
        conn.execute("INSERT INTO users VALUES (2, 'Bob', 'bob@test.com', 25)")
        conn.execute("INSERT INTO users VALUES (3, 'Charlie', NULL, NULL)")
        conn.commit()
        conn.close()
        return db_path

    def test_test_connection(self, sqlite_db: Path) -> None:
        config = ConnectionConfig(name="test", connector_type="sqlite", path=str(sqlite_db))
        conn = SQLiteConnector(config)
        assert conn.test_connection() is True
        conn.close()

    def test_list_tables(self, sqlite_db: Path) -> None:
        config = ConnectionConfig(name="test", connector_type="sqlite", path=str(sqlite_db))
        conn = SQLiteConnector(config)
        tables = conn.list_tables()
        assert "users" in tables
        conn.close()

    def test_get_schema(self, sqlite_db: Path) -> None:
        config = ConnectionConfig(name="test", connector_type="sqlite", path=str(sqlite_db))
        conn = SQLiteConnector(config)
        schema = conn.get_schema("users")
        col_names = [c[0] for c in schema]
        assert "id" in col_names
        assert "name" in col_names
        assert "email" in col_names
        conn.close()

    def test_get_row_count(self, sqlite_db: Path) -> None:
        config = ConnectionConfig(name="test", connector_type="sqlite", path=str(sqlite_db))
        conn = SQLiteConnector(config)
        assert conn.get_row_count("users") == 3  # noqa: PLR2004
        conn.close()

    def test_get_column_values(self, sqlite_db: Path) -> None:
        config = ConnectionConfig(name="test", connector_type="sqlite", path=str(sqlite_db))
        conn = SQLiteConnector(config)
        values = conn.get_column_values("users", "name")
        assert "Alice" in values
        assert "Bob" in values
        conn.close()

    def test_sample_rows(self, sqlite_db: Path) -> None:
        config = ConnectionConfig(name="test", connector_type="sqlite", path=str(sqlite_db))
        conn = SQLiteConnector(config)
        rows = conn.sample_rows("users", n=2)
        assert len(rows) == 2  # noqa: PLR2004
        assert "id" in rows[0]
        conn.close()


class TestConnectorFactory:
    def test_csv(self, tmp_path: Path) -> None:
        (tmp_path / "t.csv").write_text("a\n1\n")
        config = ConnectionConfig(name="t", connector_type="csv", path=str(tmp_path / "t.csv"))
        conn = create_connector(config)
        assert isinstance(conn, FileConnector)

    def test_sqlite(self, tmp_path: Path) -> None:
        db = tmp_path / "t.db"
        sqlite3.connect(str(db)).close()
        config = ConnectionConfig(name="t", connector_type="sqlite", path=str(db))
        conn = create_connector(config)
        assert isinstance(conn, SQLiteConnector)

    def test_unsupported(self) -> None:
        config = ConnectionConfig(name="t", connector_type="csv")  # type: ignore[arg-type]
        config_bad = ConnectionConfig(name="t", connector_type="mongodb")  # type: ignore[arg-type]
        with pytest.raises(ValueError, match="Unsupported"):
            create_connector(config_bad)
