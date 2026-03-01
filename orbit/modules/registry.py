from __future__ import annotations

from orbit.modules.base import BaseModule

_MODULES: dict[str, BaseModule] = {}


def register(module: BaseModule) -> None:
    _MODULES[module.name] = module


def get_module(name: str) -> BaseModule | None:
    return _MODULES.get(name)


def get_all_modules() -> list[BaseModule]:
    return list(_MODULES.values())


def get_module_for_command(command: str) -> BaseModule | None:
    """Find the module that handles a given command prefix."""
    cmd_parts = command.strip().split()
    if not cmd_parts:
        return None
    cmd_base = cmd_parts[0]
    for module in _MODULES.values():
        if cmd_base in module.commands:
            return module
    return None


def load_builtin_modules() -> None:
    """Load all built-in modules."""
    if _MODULES:
        return  # already loaded
    from orbit.modules import docker_mod, filesystem_mod, git_mod, k8s_mod, shell

    for mod in [shell, git_mod, docker_mod, k8s_mod, filesystem_mod]:
        register(mod.module)
