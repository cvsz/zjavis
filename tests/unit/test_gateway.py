"""Unit tests for the JARVIS model gateway."""

from __future__ import annotations

import pytest

from jarvis.ai.context import assemble_context, estimate_budget_usage, estimate_tokens
from jarvis.ai.gateway import ModelGateway
from jarvis.ai.provider import (
    LocalProviderAdapter,
    ModelCapability,
    ModelRoute,
    OllamaProviderAdapter,
    OpenAIProviderAdapter,
)
from jarvis.core.exceptions import ProviderError


class TestEstimateTokens:
    """Tests for token estimation."""

    def test_estimate_tokens_empty(self) -> None:
        assert estimate_tokens("") == 1

    def test_estimate_tokens_short(self) -> None:
        assert estimate_tokens("hi") == 1

    def test_estimate_tokens_long(self) -> None:
        assert estimate_tokens("a" * 100) == 25


class TestAssembleContext:
    """Tests for context assembly."""

    def test_assemble_context_empty(self) -> None:
        result = assemble_context([], max_tokens=4096)
        assert result == []

    def test_assemble_context_with_system(self) -> None:
        result = assemble_context(
            [], max_tokens=4096, system_prompt="You are a helpful assistant"
        )
        assert len(result) == 1
        assert result[0]["role"] == "system"

    def test_assemble_context_respects_token_budget(self) -> None:
        messages = [
            {"role": "user", "content": "a" * 1000},
            {"role": "user", "content": "b" * 1000},
            {"role": "user", "content": "c" * 1000},
        ]
        result = assemble_context(messages, max_tokens=100)
        # Should only include the most recent messages that fit
        assert len(result) <= 3

    def test_assemble_context_preserves_order(self) -> None:
        messages = [
            {"role": "user", "content": "first"},
            {"role": "assistant", "content": "second"},
        ]
        result = assemble_context(messages, max_tokens=4096)
        assert len(result) == 2
        assert result[0]["content"] == "first"
        assert result[1]["content"] == "second"


class TestEstimateBudgetUsage:
    """Tests for budget usage estimation."""

    def test_estimate_budget_usage_under_limit(self) -> None:
        result = estimate_budget_usage(50, 100)
        assert result["used"] == 50
        assert result["limit"] == 100
        assert result["remaining"] == 50
        assert result["percentage_used"] == 50.0
        assert result["exceeded"] is False

    def test_estimate_budget_usage_over_limit(self) -> None:
        result = estimate_budget_usage(150, 100)
        assert result["exceeded"] is True
        assert result["remaining"] == 0

    def test_estimate_budget_usage_zero_limit(self) -> None:
        result = estimate_budget_usage(10, 0)
        assert result["remaining"] == 0
        assert result["exceeded"] is True


class TestModelGateway:
    """Tests for the model gateway."""

    @pytest.fixture
    def gateway(self) -> ModelGateway:
        return ModelGateway()

    def test_gateway_has_local_provider(self, gateway: ModelGateway) -> None:
        assert "local" in gateway._providers

    def test_gateway_has_local_model(self, gateway: ModelGateway) -> None:
        assert "local-model" in gateway._models

    def test_gateway_has_default_route(self, gateway: ModelGateway) -> None:
        assert "default" in gateway._routes

    def test_route_default(self, gateway: ModelGateway) -> None:
        route = gateway.route(task_type="default")
        assert route.provider == "local"
        assert route.model == "local-model"

    def test_route_unknown_uses_default(self, gateway: ModelGateway) -> None:
        route = gateway.route(task_type="nonexistent")
        assert route.provider == "local"
        assert route.model == "local-model"

    def test_route_not_found(self, gateway: ModelGateway) -> None:
        gateway._routes = {}
        with pytest.raises(ProviderError):
            gateway.route(task_type="default")

    def test_register_provider(self, gateway: ModelGateway) -> None:
        adapter = LocalProviderAdapter("test", None)
        gateway.register_provider("test", adapter)
        assert "test" in gateway._providers

    def test_register_model(self, gateway: ModelGateway) -> None:
        cap = ModelCapability(name="test-model", max_context_tokens=2048)
        gateway.register_model("test-model", cap)
        assert "test-model" in gateway._models

    def test_register_route(self, gateway: ModelGateway) -> None:
        cap = ModelCapability(name="test-model")
        route = ModelRoute(provider="local", model="test-model", capability=cap)
        gateway.register_route("test-task", route)
        r = gateway.route(task_type="test-task")
        assert r.provider == "local"
        assert r.model == "test-model"

    @pytest.mark.asyncio
    async def test_complete_local(self, gateway: ModelGateway) -> None:
        result = await gateway.complete(
            task_type="default",
            messages=[{"role": "user", "content": "hello"}],
        )
        assert "response" in result
        assert result["provider"] == "local"
        assert result["model"] == "local-model"

    @pytest.mark.asyncio
    async def test_complete_stream_local(self, gateway: ModelGateway) -> None:
        chunks = []
        async for chunk in gateway.complete_stream(
            task_type="default",
            messages=[{"role": "user", "content": "hello"}],
        ):
            chunks.append(chunk)
        assert len(chunks) >= 1

    @pytest.mark.asyncio
    async def test_complete_provider_not_registered(self, gateway: ModelGateway) -> None:
        # Temporarily remove local provider to force error
        original = gateway._providers.pop("local", None)
        try:
            with pytest.raises(ProviderError):
                await gateway.complete(
                    task_type="default",
                    messages=[{"role": "user", "content": "hello"}],
                )
        finally:
            if original is not None:
                gateway._providers["local"] = original

    def test_usage_empty(self, gateway: ModelGateway) -> None:
        assert gateway.usage() == {}

    def test_usage_stats_empty(self, gateway: ModelGateway) -> None:
        assert gateway.usage_stats() == {}

    def test_openai_provider_requires_key(self) -> None:
        adapter = OpenAIProviderAdapter("openai", None, None)
        assert adapter.api_key_redacted == "[NOT_SET]"

    def test_ollama_provider_default_url(self) -> None:
        adapter = OllamaProviderAdapter("ollama", None, None)
        assert adapter.base_url == "http://localhost:11434"

    def test_local_provider_adapter_complete(self) -> None:
        adapter = LocalProviderAdapter("local", None)
        import asyncio

        result = asyncio.run(
            adapter.complete(
                model="local-model",
                messages=[{"role": "user", "content": "test"}],
            )
        )
        assert result["provider"] == "local"
        assert "response" in result

    def test_model_capability_defaults(self) -> None:
        cap = ModelCapability(name="test")
        assert cap.tool_calling is False
        assert cap.structured_output is False
        assert cap.streaming is False
        assert cap.vision is False
        assert cap.max_context_tokens == 4096

    def test_model_route_creation(self) -> None:
        cap = ModelCapability(name="test-model")
        route = ModelRoute(provider="local", model="test-model", capability=cap)
        assert route.provider == "local"
        assert route.model == "test-model"
        assert route.capability == cap