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
    """Collect Kubernetes context. Returns empty slot if kubectl is unavailable."""
    if not shutil.which("kubectl"):
        return ContextSlot(source="k8s", relevance=0.0, estimated_tokens=0, content="", available=False)

    try:
        loop = asyncio.get_event_loop()
        context = await loop.run_in_executor(None, _run, "kubectl config current-context")
        namespace = await loop.run_in_executor(
            None, _run, "kubectl config view --minify -o jsonpath='{.contexts[0].context.namespace}'"
        )
        pods = await loop.run_in_executor(None, _run, "kubectl get pods --no-headers 2>/dev/null")
        events = await loop.run_in_executor(
            None, _run, "kubectl get events --sort-by='.lastTimestamp' 2>/dev/null | tail -10"
        )

        namespace = namespace.strip("'") or "default"

        content = (
            f"Context: {context}\n"
            f"Namespace: {namespace}\n"
            f"Pods:\n{pods or '(none)'}\n"
            f"Recent events:\n{events or '(none)'}"
        )
        tokens = len(content) // 4

        return ContextSlot(
            source="k8s",
            relevance=0.7,
            estimated_tokens=tokens,
            content=content,
            available=True,
            truncation_strategy="tail",
        )
    except Exception:
        return ContextSlot(source="k8s", relevance=0.0, estimated_tokens=0, content="", available=False)
