from __future__ import annotations

import os
from pathlib import Path

from orbit.schemas.context import ContextSlot

# Key files that indicate project type
KEY_FILES = [
    "Dockerfile",
    "docker-compose.yml",
    "docker-compose.yaml",
    "Makefile",
    ".git",
    "pyproject.toml",
    "package.json",
    "Cargo.toml",
    "go.mod",
    "pom.xml",
    "build.gradle",
    "Gemfile",
    "requirements.txt",
    "Pipfile",
    ".env",
    "terraform",
    "k8s",
    "kubernetes",
    "helm",
    ".github",
    ".gitlab-ci.yml",
    "Jenkinsfile",
]


async def collect() -> ContextSlot:
    """Collect filesystem context for the current working directory."""
    try:
        cwd = Path.cwd()
        parts = [f"CWD: {cwd}"]

        # Detect key files
        found_keys = [name for name in KEY_FILES if (cwd / name).exists()]
        if found_keys:
            parts.append(f"Detected: {', '.join(found_keys)}")

        # Directory tree (depth 2, max 50 entries)
        tree_lines: list[str] = []
        count = 0
        for root, dirs, files in os.walk(cwd):
            depth = str(root).replace(str(cwd), "").count(os.sep)
            if depth > 1:
                dirs.clear()
                continue
            # Skip hidden dirs and common noise
            skip = {"node_modules", "__pycache__", ".git", "venv", ".venv"}
            dirs[:] = [d for d in sorted(dirs) if not d.startswith(".") and d not in skip]
            indent = "  " * depth
            tree_lines.append(f"{indent}{os.path.basename(root)}/")
            for f in sorted(files)[:20]:
                if not f.startswith("."):
                    tree_lines.append(f"{indent}  {f}")
                    count += 1
            if count > 50:
                tree_lines.append("  ...(truncated)")
                break

        parts.append("Tree:\n" + "\n".join(tree_lines))

        content = "\n".join(parts)
        tokens = len(content) // 4

        return ContextSlot(
            source="filesystem",
            relevance=0.4,
            estimated_tokens=tokens,
            content=content,
            available=True,
            truncation_strategy="head",
        )
    except Exception:
        return ContextSlot(source="filesystem", relevance=0.0, estimated_tokens=0, content="", available=False)
