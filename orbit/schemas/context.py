from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ContextSlot(BaseModel):
    source: str = Field(description="Identifier for the context source (e.g. 'git', 'docker', 'k8s')")
    relevance: float = Field(description="Relevance score from 0.0 to 1.0")
    estimated_tokens: int = Field(description="Estimated token count for this slot's content")
    content: str = Field(description="The actual context content")
    available: bool = Field(default=True, description="Whether this context source was available")
    truncation_strategy: Literal["head", "tail", "summary"] = Field(
        default="tail", description="How to truncate if over budget"
    )


class ContextBudget(BaseModel):
    total_tokens: int = Field(description="Total token budget for the context window")
    system_prompt_reserve: int = Field(default=500, description="Tokens reserved for system prompt")
    response_reserve: int = Field(default=2000, description="Tokens reserved for model response")
    available: int = Field(description="Tokens available for context slots after reserves")


class EnvironmentState(BaseModel):
    slots: list[ContextSlot] = Field(default_factory=list, description="Collected context slots")
    git_branch: str | None = Field(default=None, description="Current git branch name")
    k8s_namespace: str | None = Field(default=None, description="Current Kubernetes namespace")
    k8s_context: str | None = Field(default=None, description="Current Kubernetes context")
