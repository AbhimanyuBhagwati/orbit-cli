"""Tests for context collectors (git, docker, k8s, system, filesystem)."""

from __future__ import annotations

from unittest.mock import patch

import pytest


@pytest.mark.asyncio
async def test_git_unavailable():
    with patch("shutil.which", return_value=None):
        from orbit.context.git_ctx import collect

        slot = await collect()
        assert not slot.available
        assert slot.source == "git"


@pytest.mark.asyncio
async def test_git_available():
    with (
        patch("shutil.which", return_value="/usr/bin/git"),
        patch("orbit.context.git_ctx._run", return_value="main"),
    ):
        from orbit.context.git_ctx import collect

        slot = await collect()
        assert slot.available
        assert slot.source == "git"
        assert "Branch: main" in slot.content


@pytest.mark.asyncio
async def test_docker_unavailable():
    with patch("shutil.which", return_value=None):
        from orbit.context.docker_ctx import collect

        slot = await collect()
        assert not slot.available
        assert slot.source == "docker"


@pytest.mark.asyncio
async def test_docker_available():
    with (
        patch("shutil.which", return_value="/usr/bin/docker"),
        patch("orbit.context.docker_ctx._run", return_value="abc123 myapp Up"),
    ):
        from orbit.context.docker_ctx import collect

        slot = await collect()
        assert slot.available
        assert slot.source == "docker"


@pytest.mark.asyncio
async def test_k8s_unavailable():
    with patch("shutil.which", return_value=None):
        from orbit.context.k8s_ctx import collect

        slot = await collect()
        assert not slot.available
        assert slot.source == "k8s"


@pytest.mark.asyncio
async def test_k8s_available():
    with (
        patch("shutil.which", return_value="/usr/bin/kubectl"),
        patch("orbit.context.k8s_ctx._run", return_value="minikube"),
    ):
        from orbit.context.k8s_ctx import collect

        slot = await collect()
        assert slot.available
        assert slot.source == "k8s"


@pytest.mark.asyncio
async def test_system_collector():
    from orbit.context.system_ctx import collect

    slot = await collect()
    assert slot.available
    assert slot.source == "system"
    assert "OS:" in slot.content or "Shell:" in slot.content


@pytest.mark.asyncio
async def test_filesystem_collector():
    from orbit.context.filesystem_ctx import collect

    slot = await collect()
    assert slot.available
    assert slot.source == "filesystem"
    assert "CWD:" in slot.content


@pytest.mark.asyncio
async def test_git_collector_exception_returns_unavailable():
    """Collector should never crash; return unavailable on exception."""
    with (
        patch("shutil.which", return_value="/usr/bin/git"),
        patch("orbit.context.git_ctx._run", side_effect=Exception("boom")),
    ):
        from orbit.context.git_ctx import collect

        slot = await collect()
        assert not slot.available
