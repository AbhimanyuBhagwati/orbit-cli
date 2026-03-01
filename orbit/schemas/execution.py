from __future__ import annotations

from pydantic import BaseModel, Field

from orbit.schemas.plan import PlanStep


class CommandResult(BaseModel):
    command: str = Field(description="The command that was executed")
    exit_code: int = Field(description="Process exit code")
    stdout: str = Field(description="Standard output captured from the command")
    stderr: str = Field(description="Standard error captured from the command")
    duration_seconds: float = Field(description="Wall-clock execution time in seconds")
    timed_out: bool = Field(default=False, description="Whether the command was killed due to timeout")


class ExecutionRecord(BaseModel):
    step: PlanStep = Field(description="The plan step that was executed")
    result: CommandResult = Field(description="The result of executing the step")
    rollback_available: bool = Field(default=False, description="Whether a rollback command is available")
    rolled_back: bool = Field(default=False, description="Whether the step was rolled back")
