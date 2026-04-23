from __future__ import annotations

import json
from pathlib import Path

from orbit.config import DEFAULT_DATA_DIR
from orbit.schemas.data import ConnectionConfig

CONNECTIONS_DIR = DEFAULT_DATA_DIR / "connections"


def _ensure_dir() -> None:
    CONNECTIONS_DIR.mkdir(parents=True, exist_ok=True)


def save_connection(config: ConnectionConfig) -> Path:
    """Save a connection config to disk."""
    _ensure_dir()
    path = CONNECTIONS_DIR / f"{config.name}.json"
    path.write_text(config.model_dump_json(indent=2))
    return path


def load_connection(name: str) -> ConnectionConfig | None:
    """Load a connection config by name."""
    _ensure_dir()
    path = CONNECTIONS_DIR / f"{name}.json"
    if not path.exists():
        return None
    data = json.loads(path.read_text())
    return ConnectionConfig(**data)


def list_connections() -> list[str]:
    """List all saved connection names."""
    _ensure_dir()
    return sorted(p.stem for p in CONNECTIONS_DIR.glob("*.json"))


def delete_connection(name: str) -> bool:
    """Delete a saved connection."""
    path = CONNECTIONS_DIR / f"{name}.json"
    if path.exists():
        path.unlink()
        return True
    return False
