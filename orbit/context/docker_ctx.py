from __future__ import annotations

import asyncio
import shutil
import subprocess

from orbit.schemas.context import ContextSlot


def _run(cmd: str, timeout: int = 5) -> str:
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return result.stdout.strip() if result.returncode == 0 else ""
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return ""


async def collect() -> ContextSlot:
    """Collect Docker context. Returns empty slot if docker is unavailable."""
    if not shutil.which("docker"):
        return ContextSlot(source="docker", relevance=0.0, estimated_tokens=0, content="", available=False)

    try:
        loop = asyncio.get_event_loop()
        ps = await loop.run_in_executor(None, _run, 'docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Image}}"')
        compose = await loop.run_in_executor(None, _run, "docker compose ps 2>/dev/null")
        images = await loop.run_in_executor(
            None, _run, 'docker images --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}" | head -20'
        )

        parts = ["Running containers:", ps or "(none)"]
        if compose:
            parts.extend(["Compose services:", compose])
        parts.extend(["Images:", images or "(none)"])

        content = "\n".join(parts)
        tokens = len(content) // 4

        return ContextSlot(
            source="docker",
            relevance=0.6,
            estimated_tokens=tokens,
            content=content,
            available=True,
            truncation_strategy="head",
        )
    except Exception:
        return ContextSlot(source="docker", relevance=0.0, estimated_tokens=0, content="", available=False)
