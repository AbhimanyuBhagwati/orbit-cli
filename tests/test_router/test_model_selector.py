"""Tests for model selector."""

from __future__ import annotations

from unittest.mock import MagicMock

from orbit.router.model_selector import select
from orbit.schemas.plan import SubTask, TaskDecomposition


def _mock_registry(models: dict[str, set[str]]) -> MagicMock:
    registry = MagicMock()
    registry.get_models.return_value = models
    return registry


def test_select_from_priority_list():
    decomp = TaskDecomposition(
        original_goal="test",
        subtasks=[SubTask(description="do thing", capability="fast_shell", estimated_tokens=500)],
    )
    registry = _mock_registry({"qwen2.5:7b": {"fast_shell", "code_gen"}})
    result = select(decomp, registry, "fallback")
    assert result["fast_shell"] == "qwen2.5:7b"


def test_select_falls_back_to_any_with_capability():
    decomp = TaskDecomposition(
        original_goal="test",
        subtasks=[SubTask(description="do thing", capability="reasoning", estimated_tokens=500)],
    )
    registry = _mock_registry({"custom:32b": {"reasoning"}})
    result = select(decomp, registry, "fallback")
    assert result["reasoning"] == "custom:32b"


def test_select_falls_back_to_default():
    decomp = TaskDecomposition(
        original_goal="test",
        subtasks=[SubTask(description="do thing", capability="vision", estimated_tokens=500)],
    )
    registry = _mock_registry({"qwen2.5:7b": {"fast_shell"}})
    result = select(decomp, registry, "my-default")
    assert result["vision"] == "my-default"


def test_select_multiple_capabilities():
    decomp = TaskDecomposition(
        original_goal="test",
        subtasks=[
            SubTask(description="a", capability="fast_shell", estimated_tokens=500),
            SubTask(description="b", capability="reasoning", estimated_tokens=1000),
        ],
    )
    registry = _mock_registry(
        {
            "qwen2.5:7b": {"fast_shell", "code_gen"},
            "deepseek-r1:32b": {"reasoning"},
        }
    )
    result = select(decomp, registry, "fallback")
    assert "fast_shell" in result
    assert "reasoning" in result
