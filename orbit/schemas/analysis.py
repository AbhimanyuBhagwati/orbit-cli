from __future__ import annotations

from pydantic import BaseModel, Field


class WtfAnalysis(BaseModel):
    error_explanation: str = Field(description="Plain-English explanation of the error")
    root_cause: str = Field(description="Root cause analysis")
    fix_command: str | None = Field(default=None, description="Suggested command to fix the issue")
    fix_explanation: str = Field(description="Explanation of why the fix works")
    confidence: float = Field(description="Confidence score 0.0 to 1.0")
