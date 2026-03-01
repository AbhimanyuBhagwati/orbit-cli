from __future__ import annotations

import tomllib
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from orbit.config import OrbitConfig, doctor, get_config, write_config


@pytest.fixture(autouse=True)
def reset_config_singleton() -> None:
    """Reset the config singleton between tests."""
    import orbit.config

    orbit.config._config_instance = None


@pytest.fixture
def config_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Set up a temporary config directory."""
    config_dir = tmp_path / ".orbit"
    config_path = config_dir / "config.toml"
    monkeypatch.setattr("orbit.config.DEFAULT_DATA_DIR", config_dir)
    monkeypatch.setattr("orbit.config.DEFAULT_CONFIG_PATH", config_path)
    return config_dir


class TestOrbitConfig:
    def test_default_values(self) -> None:
        config = OrbitConfig()
        assert config.default_model == "qwen2.5:7b"
        assert config.safety_mode == "normal"
        assert config.ollama_host == "localhost"
        assert config.ollama_port == 11434
        assert config.max_steps == 15
        assert config.max_replans == 3
        assert config.max_llm_calls == 25


class TestGetConfig:
    def test_creates_dir_and_config(self, config_dir: Path) -> None:
        config = get_config()
        assert config_dir.exists()
        assert (config_dir / "config.toml").exists()
        assert config.default_model == "qwen2.5:7b"

    def test_singleton(self, config_dir: Path) -> None:
        c1 = get_config()
        c2 = get_config()
        assert c1 is c2


class TestWriteConfig:
    def test_write_and_read(self, config_dir: Path) -> None:
        get_config()  # ensure config exists
        write_config("default_model", "llama3:8b")
        config = get_config()
        assert config.default_model == "llama3:8b"

    def test_write_creates_key(self, config_dir: Path) -> None:
        get_config()
        write_config("safety_mode", "strict")
        with open(config_dir / "config.toml", "rb") as f:
            data = tomllib.load(f)
        assert data["safety_mode"] == "strict"

    def test_write_int_coercion(self, config_dir: Path) -> None:
        get_config()
        write_config("max_steps", "20")
        config = get_config()
        assert config.max_steps == 20


class TestDoctor:
    def test_doctor_all_pass(self, config_dir: Path) -> None:
        get_config()  # ensure config exists
        config = get_config()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"models": [{"name": "qwen2.5:7b", "size": 4000000000}]}

        with patch("orbit.config.httpx.get", return_value=mock_response):
            results = doctor(config)

        assert all(passed for _, passed, _ in results)

    def test_doctor_ollama_unreachable(self, config_dir: Path) -> None:
        get_config()
        config = get_config()

        with patch("orbit.config.httpx.get", side_effect=ConnectionError("refused")):
            results = doctor(config)

        result_dict = {name: passed for name, passed, _ in results}
        assert result_dict["Data directory"] is True
        assert result_dict["Config file"] is True
        assert result_dict["Ollama reachable"] is False
        assert result_dict["Models available"] is False
