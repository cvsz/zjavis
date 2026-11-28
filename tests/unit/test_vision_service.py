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

    def test_default_device_is_cpu(self) -> None:
        """CPU is the fallback device when no GPU device is configured."""
        provider = LocalVisionProvider()
        assert provider.device == "cpu"

    def test_device_is_reported_in_results(self) -> None:
        provider = LocalVisionProvider(device="cuda:0")
        result = asyncio.run(
            provider.describe_image(image_bytes=b"\x89PNG", prompt="x")
        )
        assert result["device"] == "cuda:0"
        result = asyncio.run(
            provider.analyze_image(image_bytes=b"\x89PNG", questions=["q"])
        )
        assert result["device"] == "cuda:0"


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
        result = asyncio.run(
            service.describe_image(image_bytes=b"\x89PNG\r\n\x1a\n", prompt="x")
        )
        assert result["error"] == "local vision not implemented"

    def test_analyze_image_delegates(self) -> None:
        service = VisionService(provider=LocalVisionProvider(), enabled=True)
        result = asyncio.run(
            service.analyze_image(
                image_bytes=b"\x89PNG\r\n\x1a\n", questions=["q"]
            )
        )
        assert result["error"] == "local vision not implemented"

    def test_default_provider_is_local(self) -> None:
        service = VisionService(enabled=True)
        assert isinstance(service.provider, LocalVisionProvider)

    def test_service_uses_cpu_fallback_device(self) -> None:
        """VisionService targets the configured device (cpu by default)."""
        service = VisionService(provider=LocalVisionProvider(), enabled=True)
        assert service.device == "cpu"

    def test_service_uses_configured_gpu_device(self) -> None:
        service = VisionService(
            provider=LocalVisionProvider(device="cuda:0"),
            enabled=True,
            device="cuda:0",
        )
        assert service.device == "cuda:0"
