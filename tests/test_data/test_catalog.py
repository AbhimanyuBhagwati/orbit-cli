from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from orbit.agents.data.catalog import build_catalog, find_similar_columns
from orbit.agents.data.connectors.factory import create_connector
from orbit.schemas.data import CatalogEntry, ConnectionConfig, DataCatalog


class TestBuildCatalog:
    @pytest.fixture()
    def csv_file(self, tmp_path: Path) -> Path:
        p = tmp_path / "sales.csv"
        p.write_text("order_id,customer_id,amount\n1,100,50.0\n2,101,75.0\n")
        return p

    @pytest.fixture()
    def sqlite_db(self, tmp_path: Path) -> Path:
        db = tmp_path / "app.db"
        conn = sqlite3.connect(str(db))
        conn.execute("CREATE TABLE customers (customer_id INTEGER, name TEXT, email TEXT)")
        conn.execute("INSERT INTO customers VALUES (100, 'Alice', 'alice@test.com')")
        conn.execute("CREATE TABLE products (product_id INTEGER, title TEXT, price REAL)")
        conn.execute("INSERT INTO products VALUES (1, 'Widget', 9.99)")
        conn.commit()
        conn.close()
        return db

    def test_catalog_from_csv(self, csv_file: Path) -> None:
        config = ConnectionConfig(name="sales", connector_type="csv", path=str(csv_file))
        connector = create_connector(config)
        catalog = build_catalog([connector])

        assert catalog.total_tables == 1
        assert catalog.total_columns == 3  # noqa: PLR2004
        assert catalog.entries[0].table_name == "sales.csv"

    def test_catalog_from_sqlite(self, sqlite_db: Path) -> None:
        config = ConnectionConfig(name="app", connector_type="sqlite", path=str(sqlite_db))
        connector = create_connector(config)
        catalog = build_catalog([connector])

        assert catalog.total_tables == 2  # noqa: PLR2004
        table_names = {e.table_name for e in catalog.entries}
        assert "customers" in table_names
        assert "products" in table_names

    def test_catalog_multiple_sources(self, csv_file: Path, sqlite_db: Path) -> None:
        c1 = create_connector(ConnectionConfig(name="sales", connector_type="csv", path=str(csv_file)))
        c2 = create_connector(ConnectionConfig(name="app", connector_type="sqlite", path=str(sqlite_db)))
        catalog = build_catalog([c1, c2])

        assert catalog.total_tables == 3  # noqa: PLR2004
        connections = {e.connection_name for e in catalog.entries}
        assert "sales" in connections
        assert "app" in connections


class TestFindSimilarColumns:
    def test_finds_customer_id_across_tables(self) -> None:
        catalog = DataCatalog(
            entries=[
                CatalogEntry(
                    connection_name="sales",
                    table_name="orders",
                    column_count=3,
                    column_names=["order_id", "customer_id", "amount"],
                    column_types=["int", "int", "float"],
                ),
                CatalogEntry(
                    connection_name="app",
                    table_name="customers",
                    column_count=3,
                    column_names=["customer_id", "name", "email"],
                    column_types=["int", "str", "str"],
                ),
            ],
            total_tables=2,
            total_columns=6,
        )
        results = find_similar_columns(catalog)
        # Should find customer_id appears in both tables
        found = False
        for cols, score, reason in results:
            tables = {t for t, c in cols}
            col_names = {c for t, c in cols}
            if "customer_id" in col_names and len(tables) > 1:
                found = True
                break
        assert found

    def test_no_duplicates_in_single_table(self) -> None:
        catalog = DataCatalog(
            entries=[
                CatalogEntry(
                    connection_name="app",
                    table_name="users",
                    column_count=2,
                    column_names=["id", "name"],
                    column_types=["int", "str"],
                ),
            ],
            total_tables=1,
            total_columns=2,
        )
        results = find_similar_columns(catalog)
        # Nothing to find with just one table
        cross_table = [r for r in results if len(set(t for t, c in r[0])) > 1]
        assert len(cross_table) == 0
