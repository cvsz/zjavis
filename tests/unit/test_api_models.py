"""Unit tests for the Phase 10 model status API response models."""

from __future__ import annotations

from dataclasses import dataclass

from jarvis.api.models import (
    ModelCapabilityResponse,
    ModelResponse,
    UsageStatsResponse,
    _capability_response,
)


@dataclass
class FakeCapability:
    name: str
    tool_calling: bool
    structured_output: bool
    streaming: bool
    vision: bool
    max_context_tokens: int


class TestCapabilityResponse:
    def test_from_capability(self) -> None:
        cap = FakeCapability(
            name="gpt-4",
            tool_calling=True,
            structured_output=True,
            streaming=True,
            vision=False,
            max_context_tokens=8192,
        )
        resp = _capability_response(cap)
        assert resp.name == "gpt-4"
        assert resp.tool_calling is True
        assert resp.structured_output is True
        assert resp.streaming is True
        assert resp.vision is False
        assert resp.max_context_tokens == 8192

    def test_model_response_defaults(self) -> None:
        resp = ModelResponse(
            name="local-model",
            provider=None,
            capability=ModelCapabilityResponse(
                name="local-model",
                tool_calling=False,
                structured_output=False,
                streaming=False,
                vision=False,
                max_context_tokens=4096,
            ),
        )
        assert resp.name == "local-model"
        assert resp.provider is None
        assert resp.capability.streaming is False

    def test_usage_stats_remaining_clamps_at_zero(self) -> None:
        resp = UsageStatsResponse(
            provider="local",
            model="local-model",
            used=150000,
            limit=100000,
            remaining=0,
            percent_used=150.0,
            exceeded=True,
        )
        assert resp.remaining == 0
        assert resp.exceeded is True
