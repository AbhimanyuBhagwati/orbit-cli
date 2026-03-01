from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class RiskAssessment(BaseModel):
    command: str = Field(description="The command being assessed")
    tier: Literal["safe", "caution", "destructive", "nuclear"] = Field(description="Risk tier classification")
    description: str = Field(description="Human-readable explanation of the risk")
    is_production: bool = Field(default=False, description="Whether the command targets a production environment")


class RollbackPlan(BaseModel):
    original_command: str = Field(description="The original command this rollback reverses")
    rollback_commands: list[str] = Field(default_factory=list, description="Ordered commands to reverse the original")
    description: str = Field(description="Human-readable description of the rollback")
