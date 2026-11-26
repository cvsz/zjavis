"""Voice interface: speech-to-text and text-to-speech provider abstraction.

Per JARVIS blueprint, voice capabilities are gated behind the
``voice_enabled`` configuration flag. Providers follow the same adapter
pattern as the model gateway. No credentials are embedded; provider API
keys come from configuration.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from jarvis.core.config import settings


class VoiceProvider(ABC):
    """Abstract base class for voice providers."""

    @abstractmethod
    async def speech_to_text(
        self, *, audio_bytes: bytes, language: str | None = None
    ) -> dict[str, Any]:
        """Convert speech audio to text.

        Args:
            audio_bytes: Raw audio data.
            language: Optional language hint (e.g. ``"en-US"``).

        Returns:
            Dict with ``text`` and optional ``confidence`` keys.
        """

    @abstractmethod
    async def text_to_speech(
        self, *, text: str, voice: str | None = None, language: str | None = None
    ) -> dict[str, Any]:
        """Convert text to speech audio.

        Args:
            text: Text to synthesize.
            voice: Optional voice identifier.
            language: Optional language hint.

        Returns:
            Dict with ``audio_bytes`` and ``content_type`` keys.
        """


class LocalVoiceProvider(VoiceProvider):
    """Local (offline) voice provider — placeholder implementation.

    Returns a stub result indicating voice processing is not available
    locally. This keeps the system functional without audio hardware
    or external credentials while the ``voice_enabled`` flag is false.
    """

    async def speech_to_text(
        self, *, audio_bytes: bytes, language: str | None = None
    ) -> dict[str, Any]:
        return {
            "text": "",
            "confidence": 0.0,
            "provider": "local",
            "error": "local voice not implemented",
        }

    async def text_to_speech(
        self, *, text: str, voice: str | None = None, language: str | None = None
    ) -> dict[str, Any]:
        return {
            "audio_bytes": b"",
            "content_type": "audio/wav",
            "provider": "local",
            "error": "local voice not implemented",
        }


class VoiceService:
    """High-level voice service that delegates to a provider.

    Raises :class:`RuntimeError` if voice is not enabled in configuration.
    """

    def __init__(
        self,
        *,
        provider: VoiceProvider | None = None,
        enabled: bool = False,
    ) -> None:
        self.provider = provider or LocalVoiceProvider()
        self.enabled = enabled

    def _require_enabled(self) -> None:
        if not self.enabled:
            raise RuntimeError(
                "Voice interface is disabled. Set JARVIS_VOICE_ENABLED=true to enable."
            )

    async def speech_to_text(
        self, *, audio_bytes: bytes, language: str | None = None
    ) -> dict[str, Any]:
        self._require_enabled()
        return await self.provider.speech_to_text(
            audio_bytes=audio_bytes, language=language
        )

    async def text_to_speech(
        self,
        *,
        text: str,
        voice: str | None = None,
        language: str | None = None,
    ) -> dict[str, Any]:
        self._require_enabled()
        return await self.provider.text_to_speech(
            text=text, voice=voice, language=language
        )


voice = VoiceService(
    provider=LocalVoiceProvider(),
    enabled=settings.voice_enabled,
)
