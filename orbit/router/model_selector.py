from __future__ import annotations

from orbit.router.model_registry import ModelRegistry
from orbit.schemas.plan import TaskDecomposition

# Priority order for each capability
CAPABILITY_PRIORITY: dict[str, list[str]] = {
    "fast_shell": ["qwen2.5:7b", "phi3", "llama3.2", "mistral"],
    "code_gen": ["qwen2.5:7b", "codellama", "qwen2.5:32b", "qwen3"],
    "reasoning": ["deepseek-r1:32b", "deepseek-r1", "qwen2.5:32b", "qwen3"],
    "long_context": ["deepseek-r1:32b", "qwen2.5:32b"],
    "vision": ["llava", "gemma3"],
    "embedding": ["nomic-embed-text", "mxbai-embed-large"],
    "general": ["qwen2.5:7b", "llama3.2", "mistral"],
}


def select(
    decomposition: TaskDecomposition,
    registry: ModelRegistry,
    default_model: str,
) -> dict[str, str]:
    """Map each needed capability to the best available model. Deterministic, no LLM."""
    available = registry.get_models()
    capability_map: dict[str, str] = {}

    needed = {st.capability for st in decomposition.subtasks}

    for cap in needed:
        capability_map[cap] = _best_model_for(cap, available, default_model)

    return capability_map


def _best_model_for(capability: str, available: dict[str, set[str]], default: str) -> str:
    """Find best available model for a capability."""
    # Check priority list first
    for model in CAPABILITY_PRIORITY.get(capability, []):
        if model in available and capability in available[model]:
            return model

    # Any model with the capability
    for model, caps in available.items():
        if capability in caps:
            return model

    return default
