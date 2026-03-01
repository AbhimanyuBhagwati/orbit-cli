from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from orbit.llm.base import LLMError


class AnthropicProvider:
    """Anthropic LLM provider stub — not yet implemented."""

    def __init__(self) -> None:
        try:
            import anthropic  # type: ignore[import-not-found]  # noqa: F401
        except ImportError as e:
            raise LLMError("Install anthropic extra: pip install orbit-cli[anthropic]") from e

    def chat(
        self,
        model: str,
        messages: list[dict[str, str]],
        schema: type[BaseModel] | None = None,
        temperature: float = 0.0,
    ) -> str | BaseModel:
        raise NotImplementedError("Anthropic provider not yet implemented")

    async def achat(
        self,
        model: str,
        messages: list[dict[str, str]],
        schema: type[BaseModel] | None = None,
        temperature: float = 0.0,
    ) -> str | BaseModel:
        raise NotImplementedError("Anthropic provider not yet implemented")

    def list_models(self) -> list[dict[str, Any]]:
        raise NotImplementedError("Anthropic provider not yet implemented")

    def model_info(self, model: str) -> dict[str, Any]:
        raise NotImplementedError("Anthropic provider not yet implemented")
