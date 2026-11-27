"""Model provider adapters.

Implements provider-specific adapters for model inference.
All adapters implement the ProviderAdapter interface from
jarvis.ai.gateway and route through the model gateway.

Providers supported:
- Local: Local inference (Ollama, llama.cpp, etc.) - no external credentials
- OpenAI: OpenAI-compatible API (requires API key)
- Ollama: Local model server
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any

import httpx

from jarvis.core.exceptions import ProviderError
from jarvis.core.logging import get_logger
from jarvis.core.security import redact_secret

logger = get_logger(__name__)


@dataclass(frozen=True)
class ModelCapability:
    """Declares a model's capabilities."""

    name: str
    tool_calling: bool = False
    structured_output: bool = False
    streaming: bool = False
    vision: bool = False
    max_context_tokens: int = 4096


@dataclass
class ModelRoute:
    """Routes tasks to a specific provider/model."""

    provider: str
    model: str
    capability: ModelCapability


class ProviderAdapter:
    """Abstract base for model provider adapters.

    Concrete adapters implement provider-specific API calls while
    the gateway handles routing, retries, and usage accounting.
    """

    def __init__(self, provider_name: str, credential: str | None) -> None:
        self.provider_name = provider_name
        self._credential = credential

    @property
    def api_key_redacted(self) -> str:
        """Return a redacted form of the credential for logging."""
        return str(redact_secret(self._credential))

    async def complete(
        self, *, model: str, messages: list[dict[str, Any]], **kwargs: Any
    ) -> dict[str, Any]:
        """Complete a chat completion. Must be implemented by subclasses."""
        raise ProviderError(
            f"Provider {self.provider_name} does not implement complete()"
        )

    def complete_stream(
        self, *, model: str, messages: list[dict[str, Any]], **kwargs: Any
    ) -> AsyncIterator[dict[str, Any]]:
        """Stream a chat completion. Must be implemented by subclasses.

        Yields chunks of the completion response.
        """
        raise ProviderError(
            f"Provider {self.provider_name} does not implement complete_stream()"
        )


class LocalProviderAdapter(ProviderAdapter):
    """Local model provider adapter (e.g., Ollama, llama.cpp).

    Used when cloud fallback is disabled and a local model server is
    available. Returns a deterministic placeholder response when no
    real local endpoint is configured, so the system can be tested
    without external credentials.
    """

    async def complete(
        self, *, model: str, messages: list[dict[str, Any]], **kwargs: Any
    ) -> dict[str, Any]:
        last_user = ""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                last_user = msg.get("content", "")
                break
        return {
            "provider": self.provider_name,
            "model": model,
            "response": f"[local echo] {last_user[:200]}",
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        }

    async def complete_stream(
        self, *, model: str, messages: list[dict[str, Any]], **kwargs: Any
    ) -> AsyncIterator[dict[str, Any]]:
        """Stream a chat completion from local provider.

        Yields chunks of the response.
        """
        result = await self.complete(model=model, messages=messages, **kwargs)
        yield result


class OpenAIProviderAdapter(ProviderAdapter):
    """OpenAI-compatible provider adapter.

    Supports OpenAI API and any OpenAI-compatible endpoint
    (e.g., local LLMs served via Ollama, vLLM, etc.).
    """

    def __init__(
        self, provider_name: str, credential: str | None, base_url: str | None = None
    ) -> None:
        super().__init__(provider_name, credential)
        self.base_url = base_url or "https://api.openai.com/v1"

    async def complete(
        self, *, model: str, messages: list[dict[str, Any]], **kwargs: Any
    ) -> dict[str, Any]:
        """Complete a chat completion via OpenAI-compatible API.

        Args:
            model: Model name.
            messages: Chat messages.
            **kwargs: Additional parameters (temperature, max_tokens, etc.).

        Returns:
            Dict with provider, model, response, and usage info.

        Raises:
            ProviderError: If the API call fails.
        """
        headers = {
            "Content-Type": "application/json",
        }
        if self._credential:
            headers["Authorization"] = f"Bearer {self._credential}"

        payload = {
            "model": model,
            "messages": messages,
            "temperature": kwargs.get("temperature", 0.7),
            "max_tokens": kwargs.get("max_tokens", 4096),
            "stream": False,
        }

        try:
            async with httpx.AsyncClient(
                timeout=kwargs.get("timeout", 120)
            ) as client, client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
            ) as response:
                response.raise_for_status()
                data = await response.json()
        except httpx.HTTPStatusError as exc:
            logger.error(
                "OpenAI provider error",
                extra={
                    "provider": self.provider_name,
                    "model": model,
                    "status_code": exc.response.status_code,
                    "error": exc.response.text[:200],
                },
            )
            raise ProviderError(
                f"OpenAI provider error: {exc.response.status_code}"
            ) from exc
        except httpx.RequestError as exc:
            logger.error(
                "OpenAI provider connection error",
                extra={
                    "provider": self.provider_name,
                    "model": model,
                    "error": str(exc),
                },
            )
            raise ProviderError(f"OpenAI provider connection error: {exc}") from exc

        content = ""
        if data.get("choices"):
            content = data["choices"][0].get("message", {}).get("content", "")

        usage = data.get("usage", {})
        return {
            "provider": self.provider_name,
            "model": model,
            "response": content,
            "usage": {
                "prompt_tokens": usage.get("prompt_tokens", 0),
                "completion_tokens": usage.get("completion_tokens", 0),
                "total_tokens": usage.get("total_tokens", 0),
            },
            "finish_reason": data.get("choices", [{}])[0].get("finish_reason", "stop"),
        }

    async def complete_stream(
        self, *, model: str, messages: list[dict[str, Any]], **kwargs: Any
    ) -> AsyncIterator[dict[str, Any]]:
        """Stream a chat completion via OpenAI-compatible API.

        Yields chunks of the response.
        """
        headers = {
            "Content-Type": "application/json",
        }
        if self._credential:
            headers["Authorization"] = f"Bearer {self._credential}"

        payload = {
            "model": model,
            "messages": messages,
            "temperature": kwargs.get("temperature", 0.7),
            "max_tokens": kwargs.get("max_tokens", 4096),
            "stream": True,
        }

        try:
            async with httpx.AsyncClient(
                timeout=kwargs.get("timeout", 120)
            ) as client, client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str.strip() == "[DONE]":
                            break
                        try:
                            data = json.loads(data_str)
                            choice = data.get("choices", [{}])[0]
                            delta = choice.get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                yield {
                                    "provider": self.provider_name,
                                    "model": model,
                                    "content": content,
                                    "finish_reason": choice.get("finish_reason"),
                                }
                        except json.JSONDecodeError:
                            continue
        except httpx.HTTPStatusError as exc:
            logger.error(
                "OpenAI provider streaming error",
                extra={
                    "provider": self.provider_name,
                    "model": model,
                    "status_code": exc.response.status_code,
                    "error": exc.response.text[:200],
                },
            )
            raise ProviderError(
                f"OpenAI provider streaming error: {exc.response.status_code}"
            ) from exc
        except httpx.RequestError as exc:
            logger.error(
                "OpenAI provider streaming connection error",
                extra={
                    "provider": self.provider_name,
                    "model": model,
                    "error": str(exc),
                },
            )
            raise ProviderError(
                f"OpenAI provider streaming connection error: {exc}"
            ) from exc


class OllamaProviderAdapter(ProviderAdapter):
    """Ollama local model provider adapter.

    Ollama is a local model server that can run models on consumer hardware.
    No external credentials required.
    """

    def __init__(
        self, provider_name: str, credential: str | None, base_url: str | None = None
    ) -> None:
        super().__init__(provider_name, credential)
        self.base_url = base_url or "http://localhost:11434"

    async def complete(
        self, *, model: str, messages: list[dict[str, Any]], **kwargs: Any
    ) -> dict[str, Any]:
        """Complete a chat completion via Ollama API.

        Args:
            model: Model name.
            messages: Chat messages.
            **kwargs: Additional parameters.

        Returns:
            Dict with provider, model, response, and usage info.

        Raises:
            ProviderError: If the API call fails.
        """
        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": kwargs.get("temperature", 0.7),
                "num_predict": kwargs.get("max_tokens", 4096),
            },
        }

        try:
            async with httpx.AsyncClient(
                timeout=kwargs.get("timeout", 120)
            ) as client, client.stream(
                "POST",
                f"{self.base_url}/api/chat",
                json=payload,
            ) as response:
                response.raise_for_status()
                data = await response.json()
        except httpx.HTTPStatusError as exc:
            logger.error(
                "Ollama provider error",
                extra={
                    "provider": self.provider_name,
                    "model": model,
                    "status_code": exc.response.status_code,
                    "error": exc.response.text[:200],
                },
            )
            raise ProviderError(
                f"Ollama provider error: {exc.response.status_code}"
            ) from exc
        except httpx.RequestError as exc:
            logger.error(
                "Ollama provider connection error",
                extra={
                    "provider": self.provider_name,
                    "model": model,
                    "error": str(exc),
                },
            )
            raise ProviderError(f"Ollama provider connection error: {exc}") from exc

        return {
            "provider": self.provider_name,
            "model": model,
            "response": data.get("message", {}).get("content", ""),
            "usage": {
                "prompt_tokens": data.get("prompt_eval_count", 0),
                "completion_tokens": data.get("eval_count", 0),
                "total_tokens": data.get("prompt_eval_count", 0)
                + data.get("eval_count", 0),
            },
            "finish_reason": "stop",
        }

    async def complete_stream(
        self, *, model: str, messages: list[dict[str, Any]], **kwargs: Any
    ) -> AsyncIterator[dict[str, Any]]:
        """Stream a chat completion via Ollama API.

        Yields chunks of the response.
        """
        payload = {
            "model": model,
            "messages": messages,
            "stream": True,
            "options": {
                "temperature": kwargs.get("temperature", 0.7),
                "num_predict": kwargs.get("max_tokens", 4096),
            },
        }

        try:
            async with httpx.AsyncClient(
                timeout=kwargs.get("timeout", 120)
            ) as client, client.stream(
                "POST",
                f"{self.base_url}/api/chat",
                json=payload,
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.strip():
                        continue
                    try:
                        data = json.loads(line)
                        message = data.get("message", {})
                        content = message.get("content", "")
                        if content:
                            yield {
                                "provider": self.provider_name,
                                "model": model,
                                "content": content,
                                "finish_reason": data.get("done", False) and "stop",
                            }
                        if data.get("done"):
                            break
                    except json.JSONDecodeError:
                        continue
        except httpx.HTTPStatusError as exc:
            logger.error(
                "Ollama provider streaming error",
                extra={
                    "provider": self.provider_name,
                    "model": model,
                    "status_code": exc.response.status_code,
                    "error": exc.response.text[:200],
                },
            )
            raise ProviderError(
                f"Ollama provider streaming error: {exc.response.status_code}"
            ) from exc
        except httpx.RequestError as exc:
            logger.error(
                "Ollama provider streaming connection error",
                extra={
                    "provider": self.provider_name,
                    "model": model,
                    "error": str(exc),
                },
            )
            raise ProviderError(
                f"Ollama provider streaming connection error: {exc}"
            ) from exc
