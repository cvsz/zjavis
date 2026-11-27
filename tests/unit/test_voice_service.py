"""Unit tests for the JARVIS Voice service stub (Phase 4 — BLOCKED without hardware/credentials)."""

from __future__ import annotations

import asyncio

import pytest

from jarvis.ai.voice import LocalVoiceProvider, VoiceService


class TestLocalVoiceProvider:
    """Tests for the local (stub) voice provider."""

    def test_speech_to_text_returns_stub(self) -> None:
        provider = LocalVoiceProvider()
        result = asyncio.run(
            provider.speech_to_text(audio_bytes=b"\x00\x01", language="en-US")
        )
        assert result["text"] == ""
        assert result["confidence"] == 0.0
        assert result["provider"] == "local"
        assert result["error"] == "local voice not implemented"

    def test_text_to_speech_returns_stub(self) -> None:
        provider = LocalVoiceProvider()
        result = asyncio.run(
            provider.text_to_speech(text="hello", voice="alloy", language="en")
        )
        assert result["audio_bytes"] == b""
        assert result["content_type"] == "audio/wav"
        assert result["provider"] == "local"
        assert result["error"] == "local voice not implemented"


class TestVoiceServiceDisabled:
    """VoiceService raises RuntimeError when disabled (secure-by-default)."""

    def test_speech_to_text_when_disabled(self) -> None:
        service = VoiceService(provider=LocalVoiceProvider(), enabled=False)
        import asyncio

        with pytest.raises(RuntimeError, match="Voice interface is disabled"):
            asyncio.run(service.speech_to_text(audio_bytes=b""))

    def test_text_to_speech_when_disabled(self) -> None:
        service = VoiceService(provider=LocalVoiceProvider(), enabled=False)
        import asyncio

        with pytest.raises(RuntimeError, match="Voice interface is disabled"):
            asyncio.run(service.text_to_speech(text="hello"))


class TestVoiceServiceEnabled:
    """VoiceService delegates to provider when enabled."""

    def test_speech_to_text_delegates(self) -> None:
        service = VoiceService(provider=LocalVoiceProvider(), enabled=True)
        result = asyncio.run(
            service.speech_to_text(audio_bytes=b"\x00", language="en-US")
        )
        assert result["error"] == "local voice not implemented"

    def test_text_to_speech_delegates(self) -> None:
        service = VoiceService(provider=LocalVoiceProvider(), enabled=True)
        import asyncio

        result = asyncio.run(service.text_to_speech(text="hi"))
        assert result["error"] == "local voice not implemented"

    def test_default_provider_is_local(self) -> None:
        service = VoiceService(enabled=True)
        assert isinstance(service.provider, LocalVoiceProvider)
