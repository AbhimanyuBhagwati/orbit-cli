from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class RunbookStep(BaseModel):
    description: str = Field(description="Human-readable description of this runbook step")
    command: str = Field(description="Shell command to execute")
    expected_exit_code: int = Field(default=0, description="Expected exit code for success")
    risk_level: Literal["safe", "caution", "destructive", "nuclear"] = Field(
        description="Risk tier for safety classification"
    )


class Runbook(BaseModel):
    name: str = Field(description="Unique name for this runbook")
    description: str = Field(description="What this runbook accomplishes")
    steps: list[RunbookStep] = Field(default_factory=list, description="Ordered steps in the runbook")
    created_at: datetime = Field(default_factory=datetime.now, description="When this runbook was created")
    updated_at: datetime = Field(default_factory=datetime.now, description="When this runbook was last updated")
