from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from orbit.config import get_config
from orbit.schemas.execution import CommandResult


def _get_db_path() -> Path:
    return get_config().data_dir / "history.db"


def _get_connection() -> sqlite3.Connection:
    db_path = _get_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            command TEXT NOT NULL,
            exit_code INTEGER NOT NULL,
            stdout TEXT,
            stderr TEXT,
            duration_seconds REAL,
            goal TEXT,
            timed_out INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    return conn


def record(result: CommandResult, goal: str | None = None) -> None:
    """Record a command execution to history."""
    conn = _get_connection()
    conn.execute(
        "INSERT INTO history (timestamp, command, exit_code, stdout, stderr, duration_seconds, goal, timed_out)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            datetime.now().isoformat(),
            result.command,
            result.exit_code,
            result.stdout[:5000],
            result.stderr[:5000],
            result.duration_seconds,
            goal,
            int(result.timed_out),
        ),
    )
    conn.commit()
    conn.close()


def search(query: str | None = None, limit: int = 20) -> list[dict[str, Any]]:
    """Search command history. Returns most recent first."""
    conn = _get_connection()
    if query:
        rows = conn.execute(
            "SELECT id, timestamp, command, exit_code, duration_seconds, goal FROM history"
            " WHERE command LIKE ? OR goal LIKE ? ORDER BY id DESC LIMIT ?",
            (f"%{query}%", f"%{query}%", limit),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT id, timestamp, command, exit_code, duration_seconds, goal FROM history ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    conn.close()
    return [
        {"id": r[0], "timestamp": r[1], "command": r[2], "exit_code": r[3], "duration": r[4], "goal": r[5]}
        for r in rows
    ]


def get_last_failed() -> dict[str, Any] | None:
    """Get the last failed command (exit_code != 0)."""
    conn = _get_connection()
    row = conn.execute(
        "SELECT command, exit_code, stdout, stderr FROM history WHERE exit_code != 0 ORDER BY id DESC LIMIT 1"
    ).fetchone()
    conn.close()
    if row:
        return {"command": row[0], "exit_code": row[1], "stdout": row[2], "stderr": row[3]}
    return None
