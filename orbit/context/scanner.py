from __future__ import annotations

import asyncio
import time

from orbit.context import docker_ctx, filesystem_ctx, git_ctx, k8s_ctx, system_ctx
from orbit.schemas.context import ContextSlot, EnvironmentState

# Relevance adjustments per (source, task_type)
RELEVANCE_MAP: dict[tuple[str, str], float] = {
    ("git", "git"): 0.95,
    ("git", "docker"): 0.3,
    ("git", "k8s"): 0.4,
    ("docker", "docker"): 0.95,
    ("docker", "git"): 0.2,
    ("docker", "k8s"): 0.4,
    ("k8s", "k8s"): 0.95,
    ("k8s", "docker"): 0.4,
    ("k8s", "git"): 0.2,
    ("system", "general"): 0.5,
    ("filesystem", "general"): 0.5,
}

_cache: dict[str, tuple[float, EnvironmentState]] = {}
_CACHE_TTL = 5.0


async def scan(task_type: str | None = None) -> EnvironmentState:
    """Run all context collectors in parallel. Results cached with 5s TTL."""
    cache_key = task_type or "__default__"
    now = time.monotonic()
    if cache_key in _cache:
        cached_time, cached_state = _cache[cache_key]
        if now - cached_time < _CACHE_TTL:
            return cached_state

    results = await asyncio.gather(
        git_ctx.collect(),
        docker_ctx.collect(),
        k8s_ctx.collect(),
        system_ctx.collect(),
        filesystem_ctx.collect(),
        return_exceptions=True,
    )

    valid_slots: list[ContextSlot] = [r for r in results if isinstance(r, ContextSlot) and r.available]

    # Adjust relevance by task type
    if task_type:
        for slot in valid_slots:
            key = (slot.source, task_type)
            if key in RELEVANCE_MAP:
                slot.relevance = RELEVANCE_MAP[key]

    # Extract structured fields from slot content
    git_branch: str | None = None
    k8s_namespace: str | None = None
    k8s_context: str | None = None

    for slot in valid_slots:
        if slot.source == "git":
            for line in slot.content.splitlines():
                if line.startswith("Branch: "):
                    git_branch = line[8:].strip() or None
        elif slot.source == "k8s":
            for line in slot.content.splitlines():
                if line.startswith("Context: "):
                    k8s_context = line[9:].strip() or None
                elif line.startswith("Namespace: "):
                    k8s_namespace = line[11:].strip() or None

    state = EnvironmentState(
        slots=valid_slots,
        git_branch=git_branch,
        k8s_namespace=k8s_namespace,
        k8s_context=k8s_context,
    )
    _cache[cache_key] = (now, state)
    return state


def clear_cache() -> None:
    """Clear the scanner cache."""
    _cache.clear()
