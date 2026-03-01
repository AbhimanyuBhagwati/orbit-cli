from __future__ import annotations

import os
import platform

from orbit.schemas.context import ContextSlot


def _redacted_env() -> str:
    """Return env var keys with redacted values."""
    lines = [f"{key}=***" for key in sorted(os.environ.keys())]
    return "\n".join(lines)


async def collect() -> ContextSlot:
    """Collect system context. Always available."""
    try:
        content = (
            f"OS: {platform.platform()}\n"
            f"Shell: {os.environ.get('SHELL', 'unknown')}\n"
            f"Python: {platform.python_version()}\n"
            f"CWD: {os.getcwd()}\n"
            f"User: {os.environ.get('USER', 'unknown')}\n"
            f"Environment variables:\n{_redacted_env()}"
        )
        tokens = len(content) // 4

        return ContextSlot(
            source="system",
            relevance=0.3,
            estimated_tokens=tokens,
            content=content,
            available=True,
            truncation_strategy="head",
        )
    except Exception:
        return ContextSlot(source="system", relevance=0.0, estimated_tokens=0, content="", available=False)
