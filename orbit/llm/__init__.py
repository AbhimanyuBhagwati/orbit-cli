from __future__ import annotations

from typing import TYPE_CHECKING

from orbit.llm.base import BaseLLM, LLMConnectionError, LLMError, LLMValidationError
from orbit.llm.ollama_provider import OllamaProvider

if TYPE_CHECKING:
    from orbit.config import OrbitConfig

__all__ = [
    "BaseLLM",
    "LLMConnectionError",
    "LLMError",
    "LLMValidationError",
    "OllamaProvider",
    "get_provider",
]


def get_provider(name: str, config: OrbitConfig) -> BaseLLM:
    """Factory function to get an LLM provider by name."""
    if name == "ollama":
        return OllamaProvider(host=config.ollama_host, port=config.ollama_port)
    elif name == "openai":
        from orbit.llm.openai_provider import OpenAIProvider

        return OpenAIProvider()
    elif name == "anthropic":
        from orbit.llm.anthropic_provider import AnthropicProvider

        return AnthropicProvider()
    else:
        raise LLMError(f"Unknown LLM provider: {name}")
