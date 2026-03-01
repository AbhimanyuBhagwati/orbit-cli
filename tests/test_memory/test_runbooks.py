"""Tests for runbook persistence (YAML)."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from orbit.schemas.runbook import Runbook, RunbookStep


@pytest.fixture
def tmp_runbooks(tmp_path):
    """Redirect runbooks to a temp directory."""
    from orbit.config import OrbitConfig

    config = OrbitConfig(data_dir=tmp_path / ".orbit")
    with patch("orbit.memory.runbooks.get_config", return_value=config):
        yield


def _sample_runbook(name: str = "deploy") -> Runbook:
    return Runbook(
        name=name,
        description="Deploy the app",
        steps=[
            RunbookStep(command="docker build -t app .", description="Build image", risk_level="caution"),
            RunbookStep(command="docker push app:latest", description="Push image", risk_level="caution"),
        ],
    )


def test_save_and_load(tmp_runbooks):
    from orbit.memory.runbooks import load, save

    rb = _sample_runbook()
    path = save(rb)
    assert path.exists()
    assert path.suffix == ".yaml"

    loaded = load("deploy")
    assert loaded is not None
    assert loaded.name == "deploy"
    assert len(loaded.steps) == 2
    assert loaded.steps[0].command == "docker build -t app ."


def test_load_nonexistent(tmp_runbooks):
    from orbit.memory.runbooks import load

    assert load("nonexistent") is None


def test_list_runbooks(tmp_runbooks):
    from orbit.memory.runbooks import list_runbooks, save

    save(_sample_runbook("alpha"))
    save(_sample_runbook("beta"))

    names = list_runbooks()
    assert names == ["alpha", "beta"]  # sorted


def test_list_runbooks_empty(tmp_runbooks):
    from orbit.memory.runbooks import list_runbooks

    assert list_runbooks() == []


def test_delete_runbook(tmp_runbooks):
    from orbit.memory.runbooks import delete, list_runbooks, save

    save(_sample_runbook("to-delete"))
    assert delete("to-delete")
    assert "to-delete" not in list_runbooks()


def test_delete_nonexistent(tmp_runbooks):
    from orbit.memory.runbooks import delete

    assert not delete("nonexistent")
