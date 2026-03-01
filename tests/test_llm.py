from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import BaseModel, Field

from orbit.llm.base import LLMConnectionError, LLMValidationError
from orbit.llm.ollama_provider import OllamaProvider


class SimpleResponse(BaseModel):
    answer: str = Field(description="The answer")
    confidence: float = Field(description="Confidence score 0-1")


@pytest.fixture
def provider() -> OllamaProvider:
    return OllamaProvider(host="localhost", port=11434)


class TestOllamaProviderChat:
    def test_chat_plain_text(self, provider: OllamaProvider) -> None:
        mock_msg = MagicMock()
        mock_msg.content = "Hello world"
        mock_resp = MagicMock()
        mock_resp.message = mock_msg

        with patch.object(provider._client, "chat", return_value=mock_resp):
            result = provider.chat("qwen2.5:7b", [{"role": "user", "content": "hi"}])

        assert result == "Hello world"

    def test_chat_structured_output(self, provider: OllamaProvider) -> None:
        mock_msg = MagicMock()
        mock_msg.content = '{"answer": "42", "confidence": 0.95}'
        mock_resp = MagicMock()
        mock_resp.message = mock_msg

        with patch.object(provider._client, "chat", return_value=mock_resp):
            result = provider.chat(
                "qwen2.5:7b",
                [{"role": "user", "content": "what is the answer?"}],
                schema=SimpleResponse,
            )

        assert isinstance(result, SimpleResponse)
        assert result.answer == "42"
        assert result.confidence == 0.95

    def test_chat_structured_output_retry(self, provider: OllamaProvider) -> None:
        """Test retry on invalid JSON first attempt."""
        bad_msg = MagicMock()
        bad_msg.content = "not json"
        bad_resp = MagicMock()
        bad_resp.message = bad_msg

        good_msg = MagicMock()
        good_msg.content = '{"answer": "retry", "confidence": 0.5}'
        good_resp = MagicMock()
        good_resp.message = good_msg

        with patch.object(provider._client, "chat", side_effect=[bad_resp, good_resp]):
            result = provider.chat(
                "qwen2.5:7b",
                [{"role": "user", "content": "test"}],
                schema=SimpleResponse,
            )

        assert isinstance(result, SimpleResponse)
        assert result.answer == "retry"

    def test_chat_structured_output_retry_fails(self, provider: OllamaProvider) -> None:
        """Test LLMValidationError after retry exhaustion."""
        bad_msg = MagicMock()
        bad_msg.content = "not json"
        bad_resp = MagicMock()
        bad_resp.message = bad_msg

        with patch.object(provider._client, "chat", return_value=bad_resp), pytest.raises(LLMValidationError):
            provider.chat(
                "qwen2.5:7b",
                [{"role": "user", "content": "test"}],
                schema=SimpleResponse,
            )

    def test_chat_connection_error(self, provider: OllamaProvider) -> None:
        with (
            patch.object(provider._client, "chat", side_effect=ConnectionError("connection refused")),
            pytest.raises(LLMConnectionError),
        ):
            provider.chat("qwen2.5:7b", [{"role": "user", "content": "hi"}])


class TestOllamaProviderAsync:
    @pytest.mark.asyncio
    async def test_achat_plain_text(self, provider: OllamaProvider) -> None:
        mock_msg = MagicMock()
        mock_msg.content = "async hello"
        mock_resp = MagicMock()
        mock_resp.message = mock_msg

        with patch.object(provider._async_client, "chat", new_callable=AsyncMock, return_value=mock_resp):
            result = await provider.achat("qwen2.5:7b", [{"role": "user", "content": "hi"}])

        assert result == "async hello"


class TestOllamaProviderListModels:
    def test_list_models(self, provider: OllamaProvider) -> None:
        mock_model = MagicMock()
        mock_model.model = "qwen2.5:7b"
        mock_model.size = 4000000000
        mock_resp = MagicMock()
        mock_resp.models = [mock_model]

        with patch.object(provider._client, "list", return_value=mock_resp):
            models = provider.list_models()

        assert len(models) == 1
        assert models[0]["name"] == "qwen2.5:7b"

    def test_list_models_connection_error(self, provider: OllamaProvider) -> None:
        with (
            patch.object(provider._client, "list", side_effect=ConnectionError("refused")),
            pytest.raises(LLMConnectionError),
        ):
            provider.list_models()
