from __future__ import annotations

from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from orbit.cli import app

runner = CliRunner()


class TestVersion:
    def test_version_flag(self) -> None:
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.output


class TestConfigShow:
    def test_config_show(self, tmp_path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
        import orbit.config

        orbit.config._config_instance = None
        config_dir = tmp_path / ".orbit"
        config_path = config_dir / "config.toml"
        monkeypatch.setattr("orbit.config.DEFAULT_DATA_DIR", config_dir)
        monkeypatch.setattr("orbit.config.DEFAULT_CONFIG_PATH", config_path)

        result = runner.invoke(app, ["config", "show"])
        assert result.exit_code == 0
        assert "default_model" in result.output


class TestConfigSet:
    def test_config_set_valid(self, tmp_path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
        import orbit.config

        orbit.config._config_instance = None
        config_dir = tmp_path / ".orbit"
        config_path = config_dir / "config.toml"
        monkeypatch.setattr("orbit.config.DEFAULT_DATA_DIR", config_dir)
        monkeypatch.setattr("orbit.config.DEFAULT_CONFIG_PATH", config_path)

        # First ensure config exists
        runner.invoke(app, ["config", "show"])
        result = runner.invoke(app, ["config", "set", "default_model", "llama3:8b"])
        assert result.exit_code == 0
        assert "Set default_model" in result.output

    def test_config_set_invalid_key(self, tmp_path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
        import orbit.config

        orbit.config._config_instance = None
        config_dir = tmp_path / ".orbit"
        config_path = config_dir / "config.toml"
        monkeypatch.setattr("orbit.config.DEFAULT_DATA_DIR", config_dir)
        monkeypatch.setattr("orbit.config.DEFAULT_CONFIG_PATH", config_path)

        result = runner.invoke(app, ["config", "set", "nonexistent", "value"])
        assert result.exit_code == 1


class TestConfigDoctor:
    def test_config_doctor_mocked(self, tmp_path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
        import orbit.config

        orbit.config._config_instance = None
        config_dir = tmp_path / ".orbit"
        config_path = config_dir / "config.toml"
        monkeypatch.setattr("orbit.config.DEFAULT_DATA_DIR", config_dir)
        monkeypatch.setattr("orbit.config.DEFAULT_CONFIG_PATH", config_path)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"models": [{"name": "qwen2.5:7b", "size": 4000000000}]}

        with patch("orbit.config.httpx.get", return_value=mock_response):
            result = runner.invoke(app, ["config", "doctor"])

        assert result.exit_code == 0


class TestSense:
    def test_sense_runs(self) -> None:
        result = runner.invoke(app, ["sense"])
        assert result.exit_code == 0


class TestModuleList:
    def test_module_list(self) -> None:
        result = runner.invoke(app, ["module", "list"])
        assert result.exit_code == 0
        assert "shell" in result.output or "git" in result.output


class TestRunbookList:
    def test_runbook_list_empty(self, tmp_path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
        import orbit.config

        orbit.config._config_instance = None
        config_dir = tmp_path / ".orbit"
        config_path = config_dir / "config.toml"
        monkeypatch.setattr("orbit.config.DEFAULT_DATA_DIR", config_dir)
        monkeypatch.setattr("orbit.config.DEFAULT_CONFIG_PATH", config_path)

        result = runner.invoke(app, ["runbook", "list"])
        assert result.exit_code == 0
        assert "No saved runbooks" in result.output


class TestHistoryList:
    def test_history_list_empty(self, tmp_path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
        import orbit.config

        orbit.config._config_instance = None
        config_dir = tmp_path / ".orbit"
        config_path = config_dir / "config.toml"
        monkeypatch.setattr("orbit.config.DEFAULT_DATA_DIR", config_dir)
        monkeypatch.setattr("orbit.config.DEFAULT_CONFIG_PATH", config_path)

        result = runner.invoke(app, ["history", "list"])
        assert result.exit_code == 0
        assert "No command history" in result.output
