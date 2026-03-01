from __future__ import annotations

import asyncio
import shutil
import subprocess

from orbit.schemas.context import ContextSlot


def _run(cmd: str, timeout: int = 5) -> str:
    """Run a shell command, return stdout. Returns empty string on failure."""
    try:
        result = subprocess.run(cmd.split(), capture_output=True, text=True, timeout=timeout)
        return result.stdout.strip() if result.returncode == 0 else ""
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return ""


async def collect() -> ContextSlot:
    """Collect git context. Returns empty slot if git is unavailable."""
    if not shutil.which("git"):
        return ContextSlot(source="git", relevance=0.0, estimated_tokens=0, content="", available=False)

    try:
        loop = asyncio.get_event_loop()
        branch = await loop.run_in_executor(None, _run, "git branch --show-current")
        status = await loop.run_in_executor(None, _run, "git status --porcelain")
        recent = await loop.run_in_executor(None, _run, "git log --oneline -5")
        diff_stat = await loop.run_in_executor(None, _run, "git diff --stat")
        remotes = await loop.run_in_executor(None, _run, "git remote -v")

        content = (
            f"Branch: {branch}\n"
            f"Changed files:\n{status}\n"
            f"Recent commits:\n{recent}\n"
            f"Diff summary:\n{diff_stat}\n"
            f"Remotes:\n{remotes}"
        )
        tokens = len(content) // 4

        return ContextSlot(
            source="git",
            relevance=0.8,
            estimated_tokens=tokens,
            content=content,
            available=True,
            truncation_strategy="tail",
        )
    except Exception:
        return ContextSlot(source="git", relevance=0.0, estimated_tokens=0, content="", available=False)
