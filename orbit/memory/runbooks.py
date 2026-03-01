from __future__ import annotations

from pathlib import Path

from orbit.config import get_config
from orbit.schemas.runbook import Runbook


def _runbook_dir() -> Path:
    d = get_config().data_dir / "runbooks"
    d.mkdir(parents=True, exist_ok=True)
    return d


def save(runbook: Runbook) -> Path:
    """Save a runbook as YAML."""
    import yaml

    path = _runbook_dir() / f"{runbook.name}.yaml"
    data = runbook.model_dump(mode="json")
    with open(path, "w") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)
    return path


def load(name: str) -> Runbook | None:
    """Load a runbook by name."""
    import yaml

    path = _runbook_dir() / f"{name}.yaml"
    if not path.exists():
        return None
    with open(path) as f:
        data = yaml.safe_load(f)
    return Runbook.model_validate(data)


def list_runbooks() -> list[str]:
    """List all saved runbook names."""
    return sorted(p.stem for p in _runbook_dir().glob("*.yaml"))


def delete(name: str) -> bool:
    """Delete a runbook. Returns True if deleted."""
    path = _runbook_dir() / f"{name}.yaml"
    if path.exists():
        path.unlink()
        return True
    return False
