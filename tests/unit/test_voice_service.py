"""Unit tests for the JARVIS Voice service stub (Phase 4 — BLOCKED without hardware/credentials)."""

from __future__ import annotations

import asyncio

import pytest

from jarvis.ai.voice import (
    AWSVoiceProvider,
    AzureVoiceProvider,
    GoogleVoiceProvider,
    LocalVoiceProvider,
    NVIDIAVoiceProvider,
    VoiceService,
    _build_provider,
)


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


class TestCloudVoiceProviders:
    """Tests for cloud voice provider stubs (no external credentials)."""

    def test_azure_no_credential_stt(self) -> None:
        provider = AzureVoiceProvider(credential=None)
        result = asyncio.run(provider.speech_to_text(audio_bytes=b"\x00\x01"))
        assert result["provider"] == "azure"
        assert result["text"] == ""
        assert result["confidence"] == 0.0
        assert "not configured" in result["error"]

    def test_azure_no_credential_tts(self) -> None:
        provider = AzureVoiceProvider(credential=None)
        result = asyncio.run(provider.text_to_speech(text="hello"))
        assert result["provider"] == "azure"
        assert result["audio_bytes"] == b""
        assert "not configured" in result["error"]

    def test_google_no_credential_stt(self) -> None:
        provider = GoogleVoiceProvider(credential=None)
        result = asyncio.run(provider.speech_to_text(audio_bytes=b"\x00\x01"))
        assert result["provider"] == "google"
        assert result["text"] == ""
        assert result["confidence"] == 0.0
        assert "not configured" in result["error"]

    def test_google_no_credential_tts(self) -> None:
        provider = GoogleVoiceProvider(credential=None)
        result = asyncio.run(provider.text_to_speech(text="hello"))
        assert result["provider"] == "google"
        assert result["audio_bytes"] == b""
        assert "not configured" in result["error"]

    def test_aws_not_implemented(self) -> None:
        provider = AWSVoiceProvider(credential="key")
        stt = asyncio.run(provider.speech_to_text(audio_bytes=b""))
        assert stt["provider"] == "aws"
        assert "SigV4" in stt["error"]
        tts = asyncio.run(provider.text_to_speech(text="hi"))
        assert tts["provider"] == "aws"
        assert "SigV4" in tts["error"]

    def test_nvidia_no_credential_stt(self) -> None:
        provider = NVIDIAVoiceProvider(credential=None)
        result = asyncio.run(provider.speech_to_text(audio_bytes=b"\x00\x01"))
        assert result["provider"] == "nvidia"
        assert result["text"] == ""
        assert result["confidence"] == 0.0
        assert "not configured" in result["error"]

    def test_nvidia_no_credential_tts(self) -> None:
        provider = NVIDIAVoiceProvider(credential=None)
        result = asyncio.run(provider.text_to_speech(text="hello"))
        assert result["provider"] == "nvidia"
        assert result["audio_bytes"] == b""
        assert "not configured" in result["error"]


class TestBuildProvider:
    """Tests for voice provider selection from configuration."""

    def test_local_provider(self) -> None:
        provider = _build_provider(
            stt_provider="local",
            stt_api_key=None,
            stt_api_url=None,
            tts_provider="local",
            tts_api_key=None,
            tts_api_url=None,
        )
        assert isinstance(provider, LocalVoiceProvider)

    def test_unknown_provider_falls_back_to_local(self) -> None:
        provider = _build_provider(
            stt_provider="nonexistent",
            stt_api_key=None,
            stt_api_url=None,
            tts_provider="nonexistent",
            tts_api_key=None,
            tts_api_url=None,
        )
        assert isinstance(provider, LocalVoiceProvider)

    def test_configured_azure_both_directions(self) -> None:
        provider = _build_provider(
            stt_provider="azure",
            stt_api_key="stt-key",
            stt_api_url=None,
            tts_provider="azure",
            tts_api_key="tts-key",
            tts_api_url=None,
        )
        assert isinstance(provider, AzureVoiceProvider)

    def test_configured_google_both_directions(self) -> None:
        provider = _build_provider(
            stt_provider="google",
            stt_api_key="stt-key",
            stt_api_url=None,
            tts_provider="google",
            tts_api_key="tts-key",
            tts_api_url=None,
        )
        assert isinstance(provider, GoogleVoiceProvider)

    def test_configured_nvidia_both_directions(self) -> None:
        provider = _build_provider(
            stt_provider="nvidia",
            stt_api_key="stt-key",
            stt_api_url=None,
            tts_provider="nvidia",
            tts_api_key="tts-key",
            tts_api_url=None,
        )
        assert isinstance(provider, NVIDIAVoiceProvider)

    def test_mixed_stt_tts_falls_back_to_local(self) -> None:
        provider = _build_provider(
            stt_provider="azure",
            stt_api_key="stt-key",
            stt_api_url=None,
            tts_provider="google",
            tts_api_key="tts-key",
            tts_api_url=None,
        )
        assert isinstance(provider, LocalVoiceProvider)

    def test_azure_no_key_falls_back_to_local(self) -> None:
        provider = _build_provider(
            stt_provider="azure",
            stt_api_key=None,
            stt_api_url=None,
            tts_provider="azure",
            tts_api_key=None,
            tts_api_url=None,
        )
        assert isinstance(provider, LocalVoiceProvider)
