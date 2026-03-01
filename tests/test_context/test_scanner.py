"""Tests for the environment scanner."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from orbit.schemas.context import ContextSlot


def _make_slot(source: str, available: bool = True, content: str = "test") -> ContextSlot:
    return ContextSlot(
        source=source,
        relevance=0.5,
        estimated_tokens=len(content) // 4,
        content=content,
        available=available,
    )


def _patches(overrides: dict[str, AsyncMock] | None = None):
    """Return a combined context manager patching all collectors + cache."""
    defaults = {
        "orbit.context.git_ctx.collect": AsyncMock(return_value=_make_slot("git", available=False)),
        "orbit.context.docker_ctx.collect": AsyncMock(return_value=_make_slot("docker", available=False)),
        "orbit.context.k8s_ctx.collect": AsyncMock(return_value=_make_slot("k8s", available=False)),
        "orbit.context.system_ctx.collect": AsyncMock(return_value=_make_slot("system")),
        "orbit.context.filesystem_ctx.collect": AsyncMock(return_value=_make_slot("filesystem")),
        "orbit.context.scanner._cache": {},
    }
    if overrides:
        defaults.update(overrides)

    # Build a combined context manager
    import contextlib

    @contextlib.contextmanager
    def combined():
        patches = [patch(k, v) for k, v in defaults.items()]
        for p in patches:
            p.start()
        try:
            yield
        finally:
            for p in patches:
                p.stop()

    return combined()


@pytest.mark.asyncio
async def test_scan_collects_all_available():
    git_slot = _make_slot("git", content="Branch: feature-x")
    sys_slot = _make_slot("system")

    with _patches(
        {
            "orbit.context.git_ctx.collect": AsyncMock(return_value=git_slot),
            "orbit.context.system_ctx.collect": AsyncMock(return_value=sys_slot),
        }
    ):
        from orbit.context.scanner import scan

        env = await scan()
        sources = {s.source for s in env.slots}
        assert "git" in sources
        assert "system" in sources
        assert "docker" not in sources  # unavailable filtered out


@pytest.mark.asyncio
async def test_scan_extracts_git_branch():
    git_slot = _make_slot("git", content="Branch: main\nSome other info")

    with _patches({"orbit.context.git_ctx.collect": AsyncMock(return_value=git_slot)}):
        from orbit.context.scanner import scan

        env = await scan()
        assert env.git_branch == "main"


@pytest.mark.asyncio
async def test_scan_tolerates_collector_exception():
    """Scanner should handle collector exceptions gracefully."""
    with _patches({"orbit.context.git_ctx.collect": AsyncMock(side_effect=Exception("boom"))}):
        from orbit.context.scanner import scan

        env = await scan()
        # Should succeed even though git collector raised
        assert any(s.source == "system" for s in env.slots)


def test_clear_cache():
    from orbit.context.scanner import _cache, clear_cache

    _cache["test"] = (0.0, None)  # type: ignore[assignment]
    clear_cache()
    assert len(_cache) == 0


@pytest.mark.asyncio
async def test_scan_relevance_adjustment():
    git_slot = _make_slot("git", content="Branch: dev")

    with _patches({"orbit.context.git_ctx.collect": AsyncMock(return_value=git_slot)}):
        from orbit.context.scanner import scan

        env = await scan(task_type="git")
        git_slots = [s for s in env.slots if s.source == "git"]
        assert git_slots[0].relevance == 0.95  # adjusted for git task_type
