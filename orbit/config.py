from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any

import httpx
import tomli_w
from pydantic import Field
from pydantic_settings import BaseSettings

DEFAULT_DATA_DIR = Path.home() / ".orbit"
DEFAULT_CONFIG_PATH = DEFAULT_DATA_DIR / "config.toml"

_config_instance: OrbitConfig | None = None


class OrbitConfig(BaseSettings):
    default_model: str = Field(default="qwen2.5:7b", description="Default Ollama model to use")
    safety_mode: str = Field(default="normal", description="Safety mode: normal, strict, or yolo")
    ollama_host: str = Field(default="localhost", description="Ollama server hostname")
    ollama_port: int = Field(default=11434, description="Ollama server port")
    max_steps: int = Field(default=15, description="Maximum steps per agent loop")
    max_replans: int = Field(default=3, description="Maximum replans per step")
    max_llm_calls: int = Field(default=25, description="Maximum total LLM calls per session")
    data_dir: Path = Field(default=DEFAULT_DATA_DIR, description="Directory for orbit data files")


def _default_config_data() -> dict[str, Any]:
    """Return default config as a plain dict, using current DEFAULT_DATA_DIR."""
    defaults = OrbitConfig()
    return {
        "default_model": defaults.default_model,
        "safety_mode": defaults.safety_mode,
        "ollama_host": defaults.ollama_host,
        "ollama_port": defaults.ollama_port,
        "max_steps": defaults.max_steps,
        "max_replans": defaults.max_replans,
        "max_llm_calls": defaults.max_llm_calls,
        "data_dir": str(DEFAULT_DATA_DIR),
    }


def get_config() -> OrbitConfig:
    """Singleton config loader. Creates ~/.orbit/ and default config if missing."""
    global _config_instance  # noqa: PLW0603
    if _config_instance is not None:
        return _config_instance

    DEFAULT_DATA_DIR.mkdir(parents=True, exist_ok=True)

    if not DEFAULT_CONFIG_PATH.exists():
        data = _default_config_data()
        with open(DEFAULT_CONFIG_PATH, "wb") as f:
            tomli_w.dump(data, f)

    # Load from TOML and construct config
    with open(DEFAULT_CONFIG_PATH, "rb") as f:
        toml_data = tomllib.load(f)

    _config_instance = OrbitConfig(**toml_data)
    return _config_instance


def write_config(key: str, value: Any) -> None:
    """Read current TOML config, update a key, and write back."""
    if DEFAULT_CONFIG_PATH.exists():
        with open(DEFAULT_CONFIG_PATH, "rb") as f:
            data = tomllib.load(f)
    else:
        data = {}

    # Coerce string values to int if the field expects int
    field_info = OrbitConfig.model_fields.get(key)
    if field_info and field_info.annotation is int and isinstance(value, str):
        value = int(value)

    data[key] = value
    with open(DEFAULT_CONFIG_PATH, "wb") as f:
        tomli_w.dump(data, f)

    # Reset singleton so next get_config() picks up changes
    global _config_instance  # noqa: PLW0603
    _config_instance = None


def doctor(config: OrbitConfig) -> list[tuple[str, bool, str]]:
    """Run health checks. Returns list of (check_name, passed, message)."""
    results: list[tuple[str, bool, str]] = []

    # Check data dir
    exists = config.data_dir.exists()
    results.append(("Data directory", exists, str(config.data_dir)))

    # Check config file
    parseable = False
    if DEFAULT_CONFIG_PATH.exists():
        try:
            with open(DEFAULT_CONFIG_PATH, "rb") as f:
                tomllib.load(f)
            parseable = True
        except Exception:
            pass
    results.append(("Config file", parseable, str(DEFAULT_CONFIG_PATH)))

    # Check Ollama connectivity
    ollama_url = f"http://{config.ollama_host}:{config.ollama_port}"
    ollama_ok = False
    models: list[str] = []
    try:
        resp = httpx.get(f"{ollama_url}/api/tags", timeout=5.0)
        if resp.status_code == 200:
            ollama_ok = True
            model_list = resp.json().get("models", [])
            models = [m.get("name", "") for m in model_list]
    except Exception:
        pass
    results.append(("Ollama reachable", ollama_ok, ollama_url))

    # Check models available
    results.append(("Models available", len(models) > 0, f"{len(models)} model(s) found"))

    # Check default model present
    default_present = any(config.default_model in m for m in models)
    results.append(("Default model", default_present, config.default_model))

    return results
