from __future__ import annotations

from orbit.agent.budget import Budget
from orbit.llm.base import BaseLLM, LLMValidationError
from orbit.schemas.context import EnvironmentState
from orbit.schemas.execution import ExecutionRecord
from orbit.schemas.plan import Plan, TaskDecomposition

PLANNER_SYSTEM_PROMPT = """You are a DevOps execution planner. Given a goal, environment context,
and task decomposition, generate a concrete execution plan.

Rules:
- Each step must have a real shell command
- Set appropriate risk_level: safe (read-only), caution (modifying), destructive (data loss), nuclear (catastrophic)
- Add rollback_command for any destructive or caution step where possible
- Set realistic timeout_seconds (default 30, longer for builds/deploys)
- Use expected_output_pattern (regex) when you know what success looks like
- Keep plans minimal: fewest steps to achieve the goal

Respond ONLY as JSON matching the provided schema."""

REPLAN_SYSTEM_PROMPT = """You are a DevOps replanner. A step in the execution plan failed.
Given the original goal, what was accomplished so far, and the error,
generate replacement steps to complete the goal.

Rules:
- Do NOT re-run steps that already succeeded
- Address the error directly
- Keep the remaining plan minimal
- If the error is unrecoverable, return an empty plan

Respond ONLY as JSON matching the provided schema."""


async def plan(
    goal: str,
    decomposition: TaskDecomposition,
    env: EnvironmentState,
    model_map: dict[str, str],
    budget: Budget,
    provider: BaseLLM,
) -> Plan:
    """Generate an execution plan using LLM structured output."""
    budget.use_llm_call()

    planning_model = model_map.get("reasoning", model_map.get("general", "qwen2.5:7b"))

    subtask_descriptions = "\n".join(
        f"- {st.description} (capability: {st.capability})" for st in decomposition.subtasks
    )
    context_text = _build_context(env)

    messages = [
        {"role": "system", "content": PLANNER_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": f"Goal: {goal}\n\nSubtasks:\n{subtask_descriptions}\n\nEnvironment:\n{context_text}",
        },
    ]

    try:
        result = await provider.achat(model=planning_model, messages=messages, schema=Plan, temperature=0.0)
        if isinstance(result, Plan):
            result.goal = goal
            return result
    except LLMValidationError:
        pass

    return Plan(goal=goal, steps=[])


async def replan(
    goal: str,
    records: list[ExecutionRecord],
    error_analysis: str,
    env: EnvironmentState,
    budget: Budget,
    provider: BaseLLM,
    model: str,
) -> Plan:
    """Generate replacement steps after a failure."""
    budget.use_llm_call()
    budget.use_replan()

    completed_summary = "\n".join(
        f"- {r.step.description}: {'OK' if r.result.exit_code == 0 else 'FAILED'}" for r in records
    )

    messages = [
        {"role": "system", "content": REPLAN_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"Goal: {goal}\n\nCompleted steps:\n{completed_summary}\n\n"
                f"Error: {error_analysis}\n\nEnvironment:\n{_build_context(env)}"
            ),
        },
    ]

    try:
        result = await provider.achat(model=model, messages=messages, schema=Plan, temperature=0.0)
        if isinstance(result, Plan):
            return result
    except LLMValidationError:
        pass

    return Plan(goal=goal, steps=[])


def _build_context(env: EnvironmentState) -> str:
    parts = [f"[{slot.source}]\n{slot.content}" for slot in env.slots if slot.available and slot.estimated_tokens > 0]
    return "\n\n".join(parts) if parts else "No context available."
