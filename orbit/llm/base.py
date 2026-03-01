from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel


class LLMError(Exception):
    """Base exception for LLM errors."""


class LLMValidationError(LLMError):
    """Raised when LLM output fails schema validation."""


class LLMConnectionError(LLMError):
    """Raised when LLM service is unreachable."""


@runtime_checkable
class BaseLLM(Protocol):
    def chat(
        self,
        model: str,
        messages: list[dict[str, str]],
        schema: type[BaseModel] | None = None,
        temperature: float = 0.0,
    ) -> str | BaseModel: ...

    async def achat(
        self,
        model: str,
        messages: list[dict[str, str]],
        schema: type[BaseModel] | None = None,
        temperature: float = 0.0,
    ) -> str | BaseModel: ...

    def list_models(self) -> list[dict[str, Any]]: ...

    def model_info(self, model: str) -> dict[str, Any]: ...
