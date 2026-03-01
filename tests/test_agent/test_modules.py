"""Tests for module system."""

from __future__ import annotations

from orbit.modules.registry import (
    _MODULES,
    get_all_modules,
    get_module,
    get_module_for_command,
    load_builtin_modules,
)


def setup_function() -> None:
    """Reset modules between tests."""
    _MODULES.clear()


def test_load_builtin_modules():
    load_builtin_modules()
    modules = get_all_modules()
    names = {m.name for m in modules}
    assert "shell" in names
    assert "git" in names
    assert "docker" in names
    assert "k8s" in names
    assert "filesystem" in names


def test_get_module():
    load_builtin_modules()
    mod = get_module("git")
    assert mod is not None
    assert mod.name == "git"


def test_get_module_unknown():
    assert get_module("nonexistent") is None


def test_get_module_for_command():
    load_builtin_modules()
    mod = get_module_for_command("git push origin main")
    assert mod is not None
    assert mod.name == "git"


def test_get_module_for_docker():
    load_builtin_modules()
    mod = get_module_for_command("docker ps")
    assert mod is not None
    assert mod.name == "docker"


def test_get_module_for_kubectl():
    load_builtin_modules()
    mod = get_module_for_command("kubectl get pods")
    assert mod is not None
    assert mod.name == "k8s"


def test_get_module_for_unknown_command():
    load_builtin_modules()
    mod = get_module_for_command("obscure_tool --flag")
    assert mod is None


def test_module_has_common_failures():
    load_builtin_modules()
    git_mod = get_module("git")
    assert git_mod is not None
    failures = git_mod.get_common_failures()
    assert len(failures) > 0


def test_module_has_system_prompt():
    load_builtin_modules()
    git_mod = get_module("git")
    assert git_mod is not None
    prompt = git_mod.get_system_prompt()
    assert len(prompt) > 0


def test_module_suggest_rollback():
    load_builtin_modules()
    k8s_mod = get_module("k8s")
    assert k8s_mod is not None
    rollback = k8s_mod.suggest_rollback("kubectl apply -f deploy.yaml")
    assert rollback is not None
    assert "delete" in rollback


def test_double_load_is_safe():
    load_builtin_modules()
    count1 = len(get_all_modules())
    load_builtin_modules()  # should not duplicate
    count2 = len(get_all_modules())
    assert count1 == count2
