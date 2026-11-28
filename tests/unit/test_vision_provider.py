"""Unit tests for the JARVIS Vision service (Phase 5 — enterprise production grade).

Covers image validation, content-type detection, the NVIDIA NIM provider
(without external credentials), the local stub, provider selection, and the
VisionService enable/disable gate. Real NVIDIA NIM integration requires GPU
hardware and live API credentials and remains BLOCKED in this environment;
these tests exercise the code paths that do not require them.
"""

from __future__ import annotations

import asyncio

import pytest

from jarvis.ai.vision import (
    MAX_IMAGE_BYTES,
    LocalVisionProvider,
    NVIDIANimVisionProvider,
    VisionService,
    _build_provider,
    detect_image_content_type,
    validate_image,
)
from jarvis.core.exceptions import ValidationError

PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"\x00" * 50
JPEG_BYTES = b"\xff\xd8\xff" + b"\x00" * 50
WEBP_BYTES = b"RIFF\x00\x00\x00\x00WEBP" + b"\x00" * 50
GIF_BYTES = b"GIF89a" + b"\x00" * 50


class TestValidateImage:
    """Tests for image payload validation."""

    def test_valid_png(self) -> None:
        content_type = validate_image(PNG_BYTES)
        assert content_type == "image/png"

    def test_valid_jpeg(self) -> None:
        content_type = validate_image(JPEG_BYTES)
        assert content_type == "image/jpeg"

    def test_valid_webp(self) -> None:
        content_type = validate_image(WEBP_BYTES)
        assert content_type == "image/webp"

    def test_empty_image_raises(self) -> None:
        with pytest.raises(ValidationError, match="Image data is empty"):
            validate_image(b"")

    def test_unsupported_format_raises(self) -> None:
        with pytest.raises(ValidationError, match="Unsupported or unrecognized"):
            validate_image(GIF_BYTES)

    def test_too_large_raises(self) -> None:
        oversized = b"\x89PNG\r\n\x1a\n" + b"\x00" * (MAX_IMAGE_BYTES + 1)
        with pytest.raises(ValidationError, match="exceeds maximum size"):
            validate_image(oversized)

    def test_at_limit_is_allowed(self) -> None:
        at_limit = b"\x89PNG\r\n\x1a\n" + b"\x00" * (MAX_IMAGE_BYTES - len(b"\x89PNG\r\n\x1a\n"))
        content_type = validate_image(at_limit)
        assert content_type == "image/png"


class TestDetectImageContentType:
    """Tests for magic-byte content type detection."""

    def test_png(self) -> None:
        assert detect_image_content_type(PNG_BYTES) == "image/png"

    def test_jpeg(self) -> None:
        assert detect_image_content_type(JPEG_BYTES) == "image/jpeg"

    def test_webp(self) -> None:
        assert detect_image_content_type(WEBP_BYTES) == "image/webp"

    def test_unknown(self) -> None:
        assert detect_image_content_type(b"\x00\x01\x02") is None

    def test_empty(self) -> None:
        assert detect_image_content_type(b"") is None


class TestLocalVisionProvider:
    """Tests for the local (stub) vision provider."""

    def test_describe_image_returns_stub(self) -> None:
        provider = LocalVisionProvider()
        result = asyncio.run(
            provider.describe_image(image_bytes=PNG_BYTES, prompt="What is this?")
        )
        assert result["description"] == ""
        assert result["confidence"] == 0.0
        assert result["provider"] == "local"
        assert result["error"] == "local vision not implemented"

    def test_analyze_image_returns_stub(self) -> None:
        provider = LocalVisionProvider()
        result = asyncio.run(
            provider.analyze_image(image_bytes=PNG_BYTES, questions=["What color?"])
        )
        assert result["answers"] == {"What color?": ""}
        assert result["provider"] == "local"

    def test_default_device_is_cpu(self) -> None:
        provider = LocalVisionProvider()
        assert provider.device == "cpu"


class TestNVIDIANimVisionProviderNoCredential:
    """Tests for NVIDIA NIM provider without credentials (no external calls)."""

    def test_no_credential_describe_raises(self) -> None:
        provider = NVIDIANimVisionProvider(credential=None)
        with pytest.raises(Exception, match="not configured"):
            asyncio.run(provider.describe_image(image_bytes=PNG_BYTES))

    def test_no_credential_analyze_raises(self) -> None:
        provider = NVIDIANimVisionProvider(credential=None)
        with pytest.raises(Exception, match="not configured"):
            asyncio.run(
                provider.analyze_image(image_bytes=PNG_BYTES, questions=["q"])
            )

    def test_defaults(self) -> None:
        provider = NVIDIANimVisionProvider(credential="key")
        assert provider.base_url == "https://integrate.api.nvidia.com/v1"
        assert provider.model == "nvidia/nemotron-3-ultra-550b-a55b"
        assert provider.device == "nvidia-nim"


class TestVisionServiceDisabled:
    """VisionService raises RuntimeError when disabled (secure-by-default)."""

    def test_describe_image_when_disabled(self) -> None:
        service = VisionService(
            provider=LocalVisionProvider(), enabled=False
        )
        with pytest.raises(RuntimeError, match="Vision interface is disabled"):
            asyncio.run(service.describe_image(image_bytes=PNG_BYTES))

    def test_analyze_image_when_disabled(self) -> None:
        service = VisionService(
            provider=LocalVisionProvider(), enabled=False
        )
        with pytest.raises(RuntimeError, match="Vision interface is disabled"):
            asyncio.run(service.analyze_image(image_bytes=PNG_BYTES, questions=["q"]))

    def test_validation_still_runs_when_disabled(self) -> None:
        """_require_enabled runs before validation; disabled raises first."""
        service = VisionService(
            provider=LocalVisionProvider(), enabled=False
        )
        with pytest.raises(RuntimeError, match="Vision interface is disabled"):
            asyncio.run(service.describe_image(image_bytes=b""))


class TestVisionServiceEnabled:
    """VisionService delegates to provider when enabled."""

    def test_describe_image_delegates(self) -> None:
        service = VisionService(
            provider=LocalVisionProvider(), enabled=True
        )
        result = asyncio.run(
            service.describe_image(image_bytes=PNG_BYTES, prompt="x")
        )
        assert result["error"] == "local vision not implemented"

    def test_analyze_image_delegates(self) -> None:
        service = VisionService(
            provider=LocalVisionProvider(), enabled=True
        )
        result = asyncio.run(
            service.analyze_image(image_bytes=PNG_BYTES, questions=["q"])
        )
        assert result["error"] == "local vision not implemented"

    def test_rejects_empty_image(self) -> None:
        service = VisionService(
            provider=LocalVisionProvider(), enabled=True
        )
        with pytest.raises(ValidationError, match="Image data is empty"):
            asyncio.run(service.describe_image(image_bytes=b""))

    def test_default_provider_is_local(self) -> None:
        service = VisionService(enabled=True)
        assert isinstance(service.provider, LocalVisionProvider)


class TestBuildProvider:
    """Tests for vision provider selection from configuration."""

    def test_local_provider(self) -> None:
        provider = _build_provider(
            provider="local", api_key=None, api_url=None, model=None
        )
        assert isinstance(provider, LocalVisionProvider)

    def test_nvidia_alias(self) -> None:
        provider = _build_provider(
            provider="nvidia",
            api_key="key",
            api_url="https://integrate.api.nvidia.com/v1",
            model="nvidia/nemotron-3-ultra-550b-a55b",
        )
        assert isinstance(provider, NVIDIANimVisionProvider)

    def test_nvidia_nim_provider(self) -> None:
        provider = _build_provider(
            provider="nvidia-nim",
            api_key="key",
            api_url=None,
            model=None,
        )
        assert isinstance(provider, NVIDIANimVisionProvider)
        assert provider.model == "nvidia/nemotron-3-ultra-550b-a55b"

    def test_unknown_provider_falls_back_to_local(self) -> None:
        provider = _build_provider(
            provider="nonexistent",
            api_key=None,
            api_url=None,
            model=None,
        )
        assert isinstance(provider, LocalVisionProvider)
