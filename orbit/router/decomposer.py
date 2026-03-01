from __future__ import annotations

from orbit.llm.base import BaseLLM, LLMValidationError
from orbit.schemas.context import EnvironmentState
from orbit.schemas.plan import SubTask, TaskDecomposition

DECOMPOSER_SYSTEM_PROMPT = """You are a DevOps task decomposer. Given a goal and environment context,
break it into subtasks. Each subtask needs a capability tag:
- "fast_shell": simple commands, listing, checking status
- "code_gen": generating code, scripts, configs
- "reasoning": complex analysis, debugging, diagnosis
- "general": anything that doesn't fit above

Keep subtasks atomic. Usually 2-5 subtasks per goal.
Respond ONLY as JSON matching the provided schema."""


async def decompose(
    goal: str,
    env: EnvironmentState,
    provider: BaseLLM,
    model: str,
) -> TaskDecomposition:
    """Decompose a goal into subtasks using LLM structured output."""
    context_summary = _build_context_summary(env)

    messages = [
        {"role": "system", "content": DECOMPOSER_SYSTEM_PROMPT},
        {"role": "user", "content": f"Goal: {goal}\n\nEnvironment:\n{context_summary}"},
    ]

    try:
        result = await provider.achat(model=model, messages=messages, schema=TaskDecomposition, temperature=0.0)
        if isinstance(result, TaskDecomposition):
            if not result.execution_order:
                result.execution_order = list(range(len(result.subtasks)))
            return result
    except LLMValidationError:
        pass

    # Fallback: single subtask
    return TaskDecomposition(
        subtasks=[SubTask(description=goal, capability="general", estimated_tokens=1000)],
        execution_order=[0],
    )


def _build_context_summary(env: EnvironmentState) -> str:
    parts: list[str] = []
    if env.git_branch:
        parts.append(f"Git branch: {env.git_branch}")
    if env.k8s_context:
        parts.append(f"K8s context: {env.k8s_context}")
    if env.k8s_namespace:
        parts.append(f"K8s namespace: {env.k8s_namespace}")
    for slot in env.slots:
        if slot.available and slot.relevance > 0.3:
            parts.append(f"{slot.source}: {slot.content[:200]}")
    return "\n".join(parts) if parts else "No environment context available."
