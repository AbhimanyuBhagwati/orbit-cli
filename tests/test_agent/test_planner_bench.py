"""Benchmark tests for the planner — mocked LLM."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from orbit.agent.budget import Budget
from orbit.agent.planner import _build_context, plan, replan
from orbit.llm.base import LLMValidationError
from orbit.schemas.context import ContextSlot, EnvironmentState
from orbit.schemas.execution import CommandResult, ExecutionRecord
from orbit.schemas.plan import Plan, PlanStep, SubTask, TaskDecomposition


@pytest.fixture
def budget() -> Budget:
    return Budget(max_steps=15, max_replans_per_step=3, max_llm_calls=25)


@pytest.fixture
def decomposition() -> TaskDecomposition:
    return TaskDecomposition(
        subtasks=[SubTask(description="list files", capability="fast_shell", estimated_tokens=500)],
        execution_order=[0],
    )


@pytest.fixture
def env() -> EnvironmentState:
    return EnvironmentState(
        slots=[
            ContextSlot(source="git", relevance=0.8, estimated_tokens=100, content="Branch: dev", available=True),
        ],
        git_branch="dev",
    )


@pytest.fixture
def empty_env() -> EnvironmentState:
    return EnvironmentState()


@pytest.fixture
def mock_provider() -> AsyncMock:
    provider = AsyncMock()
    provider.achat.return_value = Plan(
        goal="test",
        steps=[PlanStep(description="list files", command="ls -la", risk_level="safe")],
    )
    return provider


@pytest.mark.asyncio
async def test_plan_uses_reasoning_model(
    mock_provider: AsyncMock, budget: Budget, decomposition: TaskDecomposition, env: EnvironmentState
) -> None:
    model_map = {"reasoning": "deepseek-r1:32b", "general": "qwen2.5:7b"}
    await plan("list files", decomposition, env, model_map, budget, mock_provider)
    call_kwargs = mock_provider.achat.call_args
    assert call_kwargs.kwargs["model"] == "deepseek-r1:32b"


@pytest.mark.asyncio
async def test_plan_falls_back_to_general(
    mock_provider: AsyncMock, budget: Budget, decomposition: TaskDecomposition, env: EnvironmentState
) -> None:
    model_map = {"general": "qwen2.5:7b"}
    await plan("list files", decomposition, env, model_map, budget, mock_provider)
    call_kwargs = mock_provider.achat.call_args
    assert call_kwargs.kwargs["model"] == "qwen2.5:7b"


@pytest.mark.asyncio
async def test_plan_falls_back_to_default(
    mock_provider: AsyncMock, budget: Budget, decomposition: TaskDecomposition, env: EnvironmentState
) -> None:
    model_map = {}
    await plan("list files", decomposition, env, model_map, budget, mock_provider)
    call_kwargs = mock_provider.achat.call_args
    assert call_kwargs.kwargs["model"] == "qwen2.5:7b"


@pytest.mark.asyncio
async def test_plan_sets_goal(
    mock_provider: AsyncMock, budget: Budget, decomposition: TaskDecomposition, env: EnvironmentState
) -> None:
    result = await plan("my goal", decomposition, env, {}, budget, mock_provider)
    assert result.goal == "my goal"


@pytest.mark.asyncio
async def test_plan_returns_empty_on_validation_error(
    budget: Budget, decomposition: TaskDecomposition, env: EnvironmentState
) -> None:
    provider = AsyncMock()
    provider.achat.side_effect = LLMValidationError("bad json")
    result = await plan("goal", decomposition, env, {}, budget, provider)
    assert result.steps == []
    assert result.goal == "goal"


@pytest.mark.asyncio
async def test_plan_consumes_llm_budget(
    mock_provider: AsyncMock, decomposition: TaskDecomposition, env: EnvironmentState
) -> None:
    budget = Budget(max_steps=15, max_replans_per_step=3, max_llm_calls=25)
    initial_usage = budget.usage()["llm_calls"]
    await plan("goal", decomposition, env, {}, budget, mock_provider)
    assert budget.usage()["llm_calls"] == initial_usage + 1


@pytest.mark.asyncio
async def test_plan_uses_temperature_zero(
    mock_provider: AsyncMock, budget: Budget, decomposition: TaskDecomposition, env: EnvironmentState
) -> None:
    await plan("goal", decomposition, env, {}, budget, mock_provider)
    call_kwargs = mock_provider.achat.call_args
    assert call_kwargs.kwargs["temperature"] == 0.0


def test_build_context_excludes_unavailable_slots() -> None:
    env = EnvironmentState(
        slots=[
            ContextSlot(source="git", relevance=0.8, estimated_tokens=100, content="branch info", available=True),
            ContextSlot(source="docker", relevance=0.6, estimated_tokens=0, content="", available=True),
            ContextSlot(source="k8s", relevance=0.7, estimated_tokens=50, content="pod info", available=False),
        ]
    )
    ctx = _build_context(env)
    assert "branch info" in ctx
    assert "docker" not in ctx  # zero tokens
    assert "pod info" not in ctx  # unavailable


def test_build_context_empty() -> None:
    env = EnvironmentState()
    assert _build_context(env) == "No context available."


# ── Replan tests ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_replan_includes_completed_summary(env: EnvironmentState) -> None:
    provider = AsyncMock()
    provider.achat.return_value = Plan(goal="goal", steps=[])
    budget = Budget(max_steps=15, max_replans_per_step=3, max_llm_calls=25)

    step_ok = PlanStep(description="step 1", command="echo ok", risk_level="safe")
    step_fail = PlanStep(description="step 2", command="false", risk_level="safe")
    records = [
        ExecutionRecord(
            step=step_ok,
            result=CommandResult(command="echo ok", exit_code=0, stdout="ok", stderr="", duration_seconds=0.1),
        ),
        ExecutionRecord(
            step=step_fail,
            result=CommandResult(command="false", exit_code=1, stdout="", stderr="fail", duration_seconds=0.1),
        ),
    ]

    await replan("goal", records, "step 2 failed", env, budget, provider, "qwen2.5:7b")

    call_args = provider.achat.call_args
    user_msg = call_args.kwargs["messages"][1]["content"]
    assert "step 1: OK" in user_msg
    assert "step 2: FAILED" in user_msg


@pytest.mark.asyncio
async def test_replan_returns_empty_on_validation_error(env: EnvironmentState) -> None:
    provider = AsyncMock()
    provider.achat.side_effect = LLMValidationError("bad json")
    budget = Budget(max_steps=15, max_replans_per_step=3, max_llm_calls=25)

    result = await replan("goal", [], "error", env, budget, provider, "qwen2.5:7b")
    assert result.steps == []
