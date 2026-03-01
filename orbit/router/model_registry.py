from __future__ import annotations

import re

from orbit.llm.base import BaseLLM

# Built-in model → capabilities mapping
MODEL_CAPABILITIES: dict[str, set[str]] = {
    "qwen2.5:7b": {"fast_shell", "code_gen"},
    "qwen2.5:14b": {"fast_shell", "code_gen", "reasoning"},
    "qwen2.5:32b": {"reasoning", "code_gen", "fast_shell"},
    "qwen3": {"reasoning", "code_gen", "fast_shell"},
    "deepseek-r1": {"reasoning"},
    "deepseek-r1:7b": {"reasoning"},
    "deepseek-r1:14b": {"reasoning"},
    "deepseek-r1:32b": {"reasoning", "long_context"},
    "codellama": {"code_gen"},
    "llama3.2": {"fast_shell", "code_gen"},
    "llama3.1": {"fast_shell", "code_gen"},
    "llava": {"vision"},
    "gemma3": {"fast_shell", "vision"},
    "nomic-embed-text": {"embedding"},
    "mxbai-embed-large": {"embedding"},
    "phi3": {"fast_shell", "code_gen"},
    "mistral": {"fast_shell", "code_gen"},
}

# Size-based fallback capabilities
SIZE_CAPABILITIES: dict[str, set[str]] = {
    "7b": {"fast_shell"},
    "13b": {"fast_shell", "code_gen"},
    "14b": {"fast_shell", "code_gen"},
    "32b": {"reasoning", "code_gen"},
    "70b": {"reasoning", "code_gen", "long_context"},
}


class ModelRegistry:
    """Scans ollama list, caches model capabilities. No LLM calls."""

    def __init__(self) -> None:
        self._models: dict[str, set[str]] = {}
        self._context_windows: dict[str, int] = {}

    def scan(self, provider: BaseLLM) -> None:
        """Scan available models from Ollama and map capabilities."""
        models = provider.list_models()
        self._models.clear()

        for model_info in models:
            name: str = model_info["name"]
            self._models[name] = self._resolve_capabilities(name)

            # Try to get context window from model info
            try:
                info = provider.model_info(name)
                params = info.get("parameters", "") or ""
                for line in str(params).splitlines():
                    if "num_ctx" in line:
                        ctx_match = re.search(r"\d+", line)
                        if ctx_match:
                            self._context_windows[name] = int(ctx_match.group())
            except Exception:
                pass

            if name not in self._context_windows:
                self._context_windows[name] = 4096

    def _resolve_capabilities(self, model_name: str) -> set[str]:
        """Resolve capabilities: exact match → base name → size fallback → default."""
        if model_name in MODEL_CAPABILITIES:
            return MODEL_CAPABILITIES[model_name]

        base = model_name.split(":")[0] if ":" in model_name else model_name
        if base in MODEL_CAPABILITIES:
            return MODEL_CAPABILITIES[base]

        for size_tag, caps in SIZE_CAPABILITIES.items():
            if f":{size_tag}" in model_name:
                return caps

        return {"fast_shell"}

    def get_models(self) -> dict[str, set[str]]:
        return dict(self._models)

    def get_context_window(self, model: str) -> int:
        return self._context_windows.get(model, 4096)

    def models_with_capability(self, capability: str) -> list[str]:
        return [name for name, caps in self._models.items() if capability in caps]
