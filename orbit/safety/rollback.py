from __future__ import annotations

import re
from collections.abc import Callable

from orbit.schemas.safety import RollbackPlan

_GeneratorFn = Callable[[re.Match[str]], RollbackPlan]
_GENERATORS: list[tuple[re.Pattern[str], _GeneratorFn]] = []


def _register(pattern: str) -> Callable[[_GeneratorFn], _GeneratorFn]:
    compiled = re.compile(pattern)

    def decorator(func: _GeneratorFn) -> _GeneratorFn:
        _GENERATORS.append((compiled, func))
        return func

    return decorator


@_register(r"^git\s+reset\s+--hard")
def _git_reset_hard(match: re.Match[str]) -> RollbackPlan:
    return RollbackPlan(
        original_command=match.string,
        rollback_commands=["git reflog", "git reset --hard HEAD@{1}"],
        description="Undo hard reset via reflog",
    )


@_register(r"^git\s+push\s+.*--force")
def _git_force_push(match: re.Match[str]) -> RollbackPlan:
    return RollbackPlan(
        original_command=match.string,
        rollback_commands=["git reflog", "git push --force origin HEAD@{1}:branch-name"],
        description="Force push previous HEAD via reflog",
    )


@_register(r"^kubectl\s+apply\s+-f\s+(\S+)")
def _kubectl_apply(match: re.Match[str]) -> RollbackPlan:
    manifest = match.group(1)
    return RollbackPlan(
        original_command=match.string,
        rollback_commands=[f"kubectl delete -f {manifest}"],
        description=f"Delete resources from {manifest}",
    )


@_register(r"^kubectl\s+delete\s+(\S+)\s+(\S+)")
def _kubectl_delete(match: re.Match[str]) -> RollbackPlan:
    rtype, rname = match.group(1), match.group(2)
    return RollbackPlan(
        original_command=match.string,
        rollback_commands=[],
        description=f"No automatic rollback for deleted {rtype}/{rname}. Restore from backup/manifest.",
    )


@_register(r"^docker\s+compose\s+down")
def _compose_down(match: re.Match[str]) -> RollbackPlan:
    return RollbackPlan(
        original_command=match.string,
        rollback_commands=["docker compose up -d"],
        description="Restart compose services",
    )


@_register(r"^docker\s+rm\s+(\S+)")
def _docker_rm(match: re.Match[str]) -> RollbackPlan:
    return RollbackPlan(
        original_command=match.string,
        rollback_commands=[],
        description="Container must be recreated from image. No automatic rollback.",
    )


@_register(r"^rm\s+(.+)")
def _rm(match: re.Match[str]) -> RollbackPlan:
    return RollbackPlan(
        original_command=match.string,
        rollback_commands=[],
        description="File deletion is irreversible. Check backups.",
    )


def generate_rollback(command: str) -> RollbackPlan | None:
    """Generate a rollback plan for a command. Returns None if no rollback known."""
    cmd_stripped = command.strip()
    for pattern, generator in _GENERATORS:
        match = pattern.search(cmd_stripped)
        if match:
            return generator(match)
    return None
