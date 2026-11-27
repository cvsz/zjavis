"""Unit tests for the JARVIS Vision service stub (Phase 5 — BLOCKED without GPU/credentials)."""

from __future__ import annotations

import asyncio

import pytest

from jarvis.ai.vision import LocalVisionProvider, VisionService


class TestLocalVisionProvider:
    """Tests for the local (stub) vision provider."""

    def test_describe_image_returns_stub(self) -> None:
        provider = LocalVisionProvider()
        result = asyncio.run(
            provider.describe_image(image_bytes=b"\x89PNG", prompt="What is this?")
        )
        assert result["description"] == ""
        assert result["confidence"] == 0.0
        assert result["provider"] == "local"
        assert result["error"] == "local vision not implemented"

    def test_analyze_image_returns_stub(self) -> None:
        provider = LocalVisionProvider()
        result = asyncio.run(
            provider.analyze_image(image_bytes=b"\x89PNG", questions=["What color?"])
        )
        assert result["answers"] == {"What color?": ""}
        assert result["provider"] == "local"
        assert result["error"] == "local vision not implemented"


class TestVisionServiceDisabled:
    """VisionService raises RuntimeError when disabled (secure-by-default)."""

    def test_describe_image_when_disabled(self) -> None:
        service = VisionService(provider=LocalVisionProvider(), enabled=False)
        with pytest.raises(RuntimeError, match="Vision interface is disabled"):
            asyncio.run(service.describe_image(image_bytes=b""))

    def test_analyze_image_when_disabled(self) -> None:
        service = VisionService(provider=LocalVisionProvider(), enabled=False)
        with pytest.raises(RuntimeError, match="Vision interface is disabled"):
            asyncio.run(service.analyze_image(image_bytes=b"", questions=["q"]))


class TestVisionServiceEnabled:
    """VisionService delegates to provider when enabled."""

    def test_describe_image_delegates(self) -> None:
        service = VisionService(provider=LocalVisionProvider(), enabled=True)
        result = asyncio.run(service.describe_image(image_bytes=b"\x89PNG", prompt="x"))
        assert result["error"] == "local vision not implemented"

    def test_analyze_image_delegates(self) -> None:
        service = VisionService(provider=LocalVisionProvider(), enabled=True)
        result = asyncio.run(
            service.analyze_image(image_bytes=b"\x89PNG", questions=["q"])
        )
        assert result["error"] == "local vision not implemented"

    def test_default_provider_is_local(self) -> None:
        service = VisionService(enabled=True)
        assert isinstance(service.provider, LocalVisionProvider)
