"""Tests for model registry."""

from __future__ import annotations

from unittest.mock import MagicMock

from orbit.router.model_registry import ModelRegistry


def _mock_provider(models: list[dict[str, str]]) -> MagicMock:
    provider = MagicMock()
    provider.list_models.return_value = models
    provider.model_info.return_value = {"parameters": "num_ctx 4096"}
    return provider


def test_scan_known_model():
    registry = ModelRegistry()
    registry.scan(_mock_provider([{"name": "qwen2.5:7b"}]))
    models = registry.get_models()
    assert "qwen2.5:7b" in models
    assert "fast_shell" in models["qwen2.5:7b"]
    assert "code_gen" in models["qwen2.5:7b"]


def test_scan_unknown_model_gets_default_capability():
    registry = ModelRegistry()
    registry.scan(_mock_provider([{"name": "custom-model"}]))
    models = registry.get_models()
    assert "custom-model" in models
    assert models["custom-model"] == {"fast_shell"}


def test_size_based_fallback():
    registry = ModelRegistry()
    registry.scan(_mock_provider([{"name": "somemodel:32b"}]))
    models = registry.get_models()
    assert "reasoning" in models["somemodel:32b"]
    assert "code_gen" in models["somemodel:32b"]


def test_base_name_resolution():
    registry = ModelRegistry()
    registry.scan(_mock_provider([{"name": "qwen3:latest"}]))
    models = registry.get_models()
    assert "reasoning" in models["qwen3:latest"]


def test_context_window():
    registry = ModelRegistry()
    registry.scan(_mock_provider([{"name": "qwen2.5:7b"}]))
    assert registry.get_context_window("qwen2.5:7b") == 4096


def test_context_window_default():
    registry = ModelRegistry()
    assert registry.get_context_window("nonexistent") == 4096


def test_models_with_capability():
    registry = ModelRegistry()
    registry.scan(_mock_provider([{"name": "qwen2.5:7b"}, {"name": "deepseek-r1:32b"}]))
    reasoners = registry.models_with_capability("reasoning")
    assert "deepseek-r1:32b" in reasoners
    assert "qwen2.5:7b" not in reasoners
