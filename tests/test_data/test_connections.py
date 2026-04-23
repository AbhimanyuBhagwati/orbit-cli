from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from orbit.agents.data.connections import delete_connection, list_connections, load_connection, save_connection
from orbit.schemas.data import ConnectionConfig


@pytest.fixture()
def connections_dir(tmp_path: Path) -> Path:
    d = tmp_path / "connections"
    d.mkdir()
    return d


class TestConnections:
    def test_save_and_load(self, connections_dir: Path) -> None:
        with patch("orbit.agents.data.connections.CONNECTIONS_DIR", connections_dir):
            config = ConnectionConfig(name="mydb", connector_type="sqlite", path="/tmp/test.db")
            save_connection(config)
            loaded = load_connection("mydb")
            assert loaded is not None
            assert loaded.name == "mydb"
            assert loaded.connector_type == "sqlite"

    def test_load_missing(self, connections_dir: Path) -> None:
        with patch("orbit.agents.data.connections.CONNECTIONS_DIR", connections_dir):
            assert load_connection("nonexistent") is None

    def test_list_connections(self, connections_dir: Path) -> None:
        with patch("orbit.agents.data.connections.CONNECTIONS_DIR", connections_dir):
            save_connection(ConnectionConfig(name="alpha", connector_type="csv", path="/tmp/a.csv"))
            save_connection(ConnectionConfig(name="beta", connector_type="sqlite", path="/tmp/b.db"))
            names = list_connections()
            assert "alpha" in names
            assert "beta" in names

    def test_delete_connection(self, connections_dir: Path) -> None:
        with patch("orbit.agents.data.connections.CONNECTIONS_DIR", connections_dir):
            save_connection(ConnectionConfig(name="temp", connector_type="csv", path="/tmp/t.csv"))
            assert delete_connection("temp") is True
            assert load_connection("temp") is None

    def test_delete_missing(self, connections_dir: Path) -> None:
        with patch("orbit.agents.data.connections.CONNECTIONS_DIR", connections_dir):
            assert delete_connection("nope") is False
