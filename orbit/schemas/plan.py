from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class PlanStep(BaseModel):
    description: str = Field(description="Human-readable description of what this step does")
    command: str = Field(description="Shell command to execute")
    risk_level: Literal["safe", "caution", "destructive", "nuclear"] = Field(
        description="Risk tier for safety classification"
    )
    rollback_command: str | None = Field(default=None, description="Command to reverse this step's effects")
    expected_exit_code: int = Field(default=0, description="Expected exit code for success")
    expected_output_pattern: str | None = Field(
        default=None, description="Regex pattern to match against stdout for success verification"
    )
    timeout_seconds: int = Field(default=30, description="Maximum seconds to wait for command completion")
    requires_context: list[str] = Field(
        default_factory=list, description="Context slot sources needed before executing this step"
    )


class Plan(BaseModel):
    goal: str = Field(description="The original user goal this plan addresses")
    steps: list[PlanStep] = Field(default_factory=list, description="Ordered list of steps to achieve the goal")


class SubTask(BaseModel):
    description: str = Field(description="What this subtask accomplishes")
    capability: str = Field(description="Required model capability tag (e.g. 'code', 'reasoning', 'general')")
    context_needed: list[str] = Field(default_factory=list, description="Context slot sources this subtask needs")
    estimated_tokens: int = Field(description="Estimated token budget for this subtask")


class TaskDecomposition(BaseModel):
    subtasks: list[SubTask] = Field(default_factory=list, description="Decomposed subtasks")
    execution_order: list[int] = Field(
        default_factory=list, description="Indices into subtasks list defining execution order"
    )
