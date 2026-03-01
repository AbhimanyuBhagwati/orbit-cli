"""Benchmark tests for the decomposer — mocked LLM."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from orbit.llm.base import LLMValidationError
from orbit.router.decomposer import _build_context_summary, decompose
from orbit.schemas.context import ContextSlot, EnvironmentState
from orbit.schemas.plan import SubTask, TaskDecomposition


@pytest.fixture
def env() -> EnvironmentState:
    return EnvironmentState(
        slots=[
            ContextSlot(source="git", relevance=0.8, estimated_tokens=100, content="Branch: dev\nStatus: clean"),
            ContextSlot(source="docker", relevance=0.6, estimated_tokens=50, content="2 containers running"),
        ],
        git_branch="dev",
    )


@pytest.mark.asyncio
async def test_decompose_happy_path(env: EnvironmentState) -> None:
    provider = AsyncMock()
    provider.achat.return_value = TaskDecomposition(
        subtasks=[
            SubTask(description="check git status", capability="fast_shell", estimated_tokens=500),
            SubTask(description="analyze code", capability="reasoning", estimated_tokens=1000),
        ],
        execution_order=[0, 1],
    )

    result = await decompose("deploy app", env, provider, "qwen2.5:7b")
    assert len(result.subtasks) == 2
    assert result.execution_order == [0, 1]


@pytest.mark.asyncio
async def test_decompose_fills_empty_execution_order(env: EnvironmentState) -> None:
    provider = AsyncMock()
    provider.achat.return_value = TaskDecomposition(
        subtasks=[
            SubTask(description="step 1", capability="fast_shell", estimated_tokens=500),
            SubTask(description="step 2", capability="general", estimated_tokens=500),
        ],
        execution_order=[],
    )

    result = await decompose("goal", env, provider, "qwen2.5:7b")
    assert result.execution_order == [0, 1]


@pytest.mark.asyncio
async def test_decompose_fallback_on_llm_error(env: EnvironmentState) -> None:
    provider = AsyncMock()
    provider.achat.side_effect = LLMValidationError("bad json")

    result = await decompose("deploy app", env, provider, "qwen2.5:7b")
    assert len(result.subtasks) == 1
    assert result.subtasks[0].capability == "general"
    assert result.subtasks[0].description == "deploy app"
    assert result.execution_order == [0]


def test_context_summary_includes_git_branch() -> None:
    env = EnvironmentState(git_branch="main")
    summary = _build_context_summary(env)
    assert "Git branch: main" in summary


def test_context_summary_includes_k8s() -> None:
    env = EnvironmentState(k8s_context="prod-cluster", k8s_namespace="default")
    summary = _build_context_summary(env)
    assert "K8s context: prod-cluster" in summary
    assert "K8s namespace: default" in summary


def test_context_summary_filters_low_relevance() -> None:
    env = EnvironmentState(
        slots=[
            ContextSlot(source="system", relevance=0.2, estimated_tokens=100, content="OS: Linux"),
            ContextSlot(source="git", relevance=0.8, estimated_tokens=100, content="Branch: dev"),
        ]
    )
    summary = _build_context_summary(env)
    assert "git:" in summary.lower() or "Branch: dev" in summary
    assert "OS: Linux" not in summary  # relevance 0.2 < 0.3 threshold


def test_context_summary_empty_env() -> None:
    env = EnvironmentState()
    summary = _build_context_summary(env)
    assert "No environment context" in summary
