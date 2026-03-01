"""Tests for command history (SQLite)."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from orbit.schemas.execution import CommandResult


@pytest.fixture
def tmp_db(tmp_path):
    """Redirect history DB to a temp directory."""
    from orbit.config import OrbitConfig

    config = OrbitConfig(data_dir=tmp_path / ".orbit")
    with patch("orbit.memory.history.get_config", return_value=config):
        yield


def _result(cmd: str = "ls", exit_code: int = 0) -> CommandResult:
    return CommandResult(
        command=cmd,
        exit_code=exit_code,
        stdout="output",
        stderr="",
        duration_seconds=0.1,
    )


def test_record_and_search(tmp_db):
    from orbit.memory.history import record, search

    record(_result("ls -la"), goal="list files")
    record(_result("git status"), goal="check git")

    results = search()
    assert len(results) == 2
    assert results[0]["command"] == "git status"  # most recent first


def test_search_with_query(tmp_db):
    from orbit.memory.history import record, search

    record(_result("ls -la"), goal="list files")
    record(_result("git status"), goal="check git")

    results = search(query="git")
    assert len(results) == 1
    assert results[0]["command"] == "git status"


def test_search_limit(tmp_db):
    from orbit.memory.history import record, search

    for i in range(10):
        record(_result(f"cmd-{i}"))

    results = search(limit=3)
    assert len(results) == 3


def test_get_last_failed(tmp_db):
    from orbit.memory.history import get_last_failed, record

    record(_result("good-cmd", exit_code=0))
    record(_result("bad-cmd", exit_code=1))
    record(_result("another-good", exit_code=0))

    failed = get_last_failed()
    assert failed is not None
    assert failed["command"] == "bad-cmd"
    assert failed["exit_code"] == 1


def test_get_last_failed_none(tmp_db):
    from orbit.memory.history import get_last_failed, record

    record(_result("good-cmd", exit_code=0))
    assert get_last_failed() is None
