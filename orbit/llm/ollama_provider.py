from __future__ import annotations

from typing import Any

import ollama
from pydantic import BaseModel

from orbit.llm.base import LLMConnectionError, LLMError, LLMValidationError


class OllamaProvider:
    """Ollama LLM provider with structured output support."""

    def __init__(self, host: str = "localhost", port: int = 11434) -> None:
        self._host = host
        self._port = port
        self._client = ollama.Client(host=f"http://{host}:{port}")
        self._async_client = ollama.AsyncClient(host=f"http://{host}:{port}")

    def chat(
        self,
        model: str,
        messages: list[dict[str, str]],
        schema: type[BaseModel] | None = None,
        temperature: float = 0.0,
    ) -> str | BaseModel:
        """Synchronous chat with optional structured output."""
        kwargs: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "options": {"temperature": 0.0 if schema else temperature},
        }
        if schema is not None:
            kwargs["format"] = schema.model_json_schema()

        try:
            response = self._client.chat(**kwargs)
        except ollama.ResponseError as e:
            raise LLMError(f"Ollama error: {e}") from e
        except Exception as e:
            if "connect" in str(e).lower() or "refused" in str(e).lower():
                raise LLMConnectionError(f"Cannot reach Ollama at {self._host}:{self._port}") from e
            raise LLMError(f"Ollama error: {e}") from e

        content = response.message.content or ""

        if schema is None:
            return content

        return self._validate_response(content, schema, model, messages)

    async def achat(
        self,
        model: str,
        messages: list[dict[str, str]],
        schema: type[BaseModel] | None = None,
        temperature: float = 0.0,
    ) -> str | BaseModel:
        """Async chat with optional structured output."""
        kwargs: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "options": {"temperature": 0.0 if schema else temperature},
        }
        if schema is not None:
            kwargs["format"] = schema.model_json_schema()

        try:
            response = await self._async_client.chat(**kwargs)
        except ollama.ResponseError as e:
            raise LLMError(f"Ollama error: {e}") from e
        except Exception as e:
            if "connect" in str(e).lower() or "refused" in str(e).lower():
                raise LLMConnectionError(f"Cannot reach Ollama at {self._host}:{self._port}") from e
            raise LLMError(f"Ollama error: {e}") from e

        content = response.message.content or ""

        if schema is None:
            return content

        return self._validate_response(content, schema, model, messages)

    def _validate_response(
        self,
        content: str,
        schema: type[BaseModel],
        model: str,
        messages: list[dict[str, str]],
    ) -> BaseModel:
        """Validate and retry once on failure."""
        try:
            return schema.model_validate_json(content)
        except Exception:
            pass

        # Retry once
        try:
            retry_messages = [*messages, {"role": "assistant", "content": content}]
            retry_messages.append(
                {
                    "role": "user",
                    "content": "Your previous response was not valid JSON matching the schema. Please try again.",
                }
            )
            response = self._client.chat(
                model=model,
                messages=retry_messages,
                format=schema.model_json_schema(),
                options={"temperature": 0.0},
            )
            retry_content = response.message.content or ""
            return schema.model_validate_json(retry_content)
        except Exception as e:
            raise LLMValidationError(f"Failed to parse LLM response after retry: {e}") from e

    def list_models(self) -> list[dict[str, Any]]:
        """List available models."""
        try:
            response = self._client.list()
            return [{"name": m.model, "size": m.size} for m in response.models]
        except Exception as e:
            raise LLMConnectionError(f"Cannot list models: {e}") from e

    def model_info(self, model: str) -> dict[str, Any]:
        """Get model details."""
        try:
            response = self._client.show(model)
            return {"modelfile": response.modelfile, "parameters": response.parameters, "template": response.template}
        except Exception as e:
            raise LLMError(f"Cannot get model info: {e}") from e
