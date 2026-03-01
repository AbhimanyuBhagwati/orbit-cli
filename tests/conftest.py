from __future__ import annotations

from pathlib import Path

import pytest

from orbit.config import OrbitConfig
from orbit.schemas.context import ContextBudget, ContextSlot, EnvironmentState
from orbit.schemas.execution import CommandResult
from orbit.schemas.plan import Plan, PlanStep


@pytest.fixture
def sample_plan_step() -> PlanStep:
    return PlanStep(
        description="List files",
        command="ls -la",
        risk_level="safe",
        rollback_command=None,
    )


@pytest.fixture
def sample_plan(sample_plan_step: PlanStep) -> Plan:
    return Plan(goal="Explore directory", steps=[sample_plan_step])


@pytest.fixture
def sample_command_result() -> CommandResult:
    return CommandResult(
        command="ls -la",
        exit_code=0,
        stdout="total 0\ndrwxr-xr-x  2 user user 64 Jan 1 00:00 .\n",
        stderr="",
        duration_seconds=0.05,
    )


@pytest.fixture
def sample_env_state() -> EnvironmentState:
    return EnvironmentState(
        slots=[
            ContextSlot(
                source="git",
                relevance=0.9,
                estimated_tokens=100,
                content="branch: main",
                available=True,
            )
        ],
        git_branch="main",
    )


@pytest.fixture
def sample_context_budget() -> ContextBudget:
    return ContextBudget(total_tokens=4096, available=1596)


@pytest.fixture
def mock_config(tmp_path: Path) -> OrbitConfig:
    return OrbitConfig(
        default_model="qwen2.5:7b",
        data_dir=tmp_path / ".orbit",
        ollama_host="localhost",
        ollama_port=11434,
    )
