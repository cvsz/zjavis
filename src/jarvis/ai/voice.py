"""Voice interface: speech-to-text and text-to-speech provider abstraction.

Per JARVIS blueprint, voice capabilities are gated behind the
``voice_enabled`` configuration flag. Providers follow the same adapter
pattern as the model gateway. No credentials are embedded; provider API
keys come from configuration.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import httpx

from jarvis.core.config import settings
from jarvis.core.exceptions import ProviderError
from jarvis.core.logging import get_logger
from jarvis.core.security import redact_secret

logger = get_logger(__name__)


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


class AzureVoiceProvider(VoiceProvider):
    """Azure Speech Services provider for STT and TTS.

    Uses the Azure Speech REST APIs (speech-to-text batch/short-audio and
    text-to-speech). Authentication is Bearer-token based via the API key.
    No credentials are embedded; the API key comes from configuration.
    """

    def __init__(
        self,
        *,
        credential: str | None,
        base_url: str | None = None,
    ) -> None:
        self._credential = credential
        self.base_url = base_url or "https://{region}.tts.speech.microsoft.com"
        self._api_key_redacted = redact_secret(credential)

    async def speech_to_text(
        self, *, audio_bytes: bytes, language: str | None = None
    ) -> dict[str, Any]:
        """Convert speech audio to text via Azure Speech-to-Text."""
        if not self._credential:
            return {
                "text": "",
                "confidence": 0.0,
                "provider": "azure",
                "error": "Azure STT API key not configured",
            }
        headers = {
            "Ocp-Apim-Subscription-Key": self._credential,
            "Content-Type": "audio/wav",
        }
        params: dict[str, str] = {}
        if language:
            params["language"] = language
        try:
            async with httpx.AsyncClient(timeout=120) as client:
                response = await client.post(
                    f"{self.base_url}/speech/recognize",
                    headers=headers,
                    params=params or None,
                    content=audio_bytes,
                )
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPStatusError as exc:
            logger.error(
                "Azure STT error",
                extra={
                    "provider": "azure",
                    "status_code": exc.response.status_code,
                    "error": exc.response.text[:200],
                },
            )
            raise ProviderError(f"Azure STT error: {exc.response.status_code}") from exc
        except httpx.RequestError as exc:
            logger.error(
                "Azure STT connection error",
                extra={"provider": "azure", "error": str(exc)},
            )
            raise ProviderError(f"Azure STT connection error: {exc}") from exc

        return {
            "text": data.get("DisplayText", data.get("text", "")),
            "confidence": float(data.get("Confidence", 0.0) or 0.0),
            "provider": "azure",
        }

    async def text_to_speech(
        self, *, text: str, voice: str | None = None, language: str | None = None
    ) -> dict[str, Any]:
        """Convert text to speech audio via Azure Text-to-Speech."""
        if not self._credential:
            return {
                "audio_bytes": b"",
                "content_type": "audio/wav",
                "provider": "azure",
                "error": "Azure TTS API key not configured",
            }
        headers = {
            "Ocp-Apim-Subscription-Key": self._credential,
            "Content-Type": "application/ssml+xml",
            "X-Microsoft-OutputFormat": "audio-16khz-128kbitrate-mono-mp3",
        }
        voice_name = voice or "en-US-AriaNeural"
        lang = language or "en-US"
        ssml = (
            f"<speak version='1.0' xml:lang='{lang}'>"
            f"<voice xml:lang='{lang}' xml:gender='Female' name='{voice_name}'>"
            f"{text}</voice></speak>"
        )
        try:
            async with httpx.AsyncClient(timeout=120) as client:
                response = await client.post(
                    f"{self.base_url}/tts",
                    headers=headers,
                    content=ssml.encode("utf-8"),
                )
                response.raise_for_status()
                audio_bytes = response.content
        except httpx.HTTPStatusError as exc:
            logger.error(
                "Azure TTS error",
                extra={
                    "provider": "azure",
                    "status_code": exc.response.status_code,
                    "error": exc.response.text[:200],
                },
            )
            raise ProviderError(f"Azure TTS error: {exc.response.status_code}") from exc
        except httpx.RequestError as exc:
            logger.error(
                "Azure TTS connection error",
                extra={"provider": "azure", "error": str(exc)},
            )
            raise ProviderError(f"Azure TTS connection error: {exc}") from exc

        return {
            "audio_bytes": audio_bytes,
            "content_type": "audio/mpeg",
            "provider": "azure",
        }


class GoogleVoiceProvider(VoiceProvider):
    """Google Cloud Speech-to-Text and Text-to-Speech provider.

    Uses Google Cloud Speech and Text-to-Speech REST APIs with Bearer-token
    authentication via the API key. No credentials are embedded.
    """

    def __init__(
        self,
        *,
        credential: str | None,
        base_url: str | None = None,
    ) -> None:
        self._credential = credential
        self.base_url = base_url or "https://speech.googleapis.com/v1"
        self._api_key_redacted = redact_secret(credential)

    async def speech_to_text(
        self, *, audio_bytes: bytes, language: str | None = None
    ) -> dict[str, Any]:
        """Convert speech audio to text via Google Speech-to-Text."""
        if not self._credential:
            return {
                "text": "",
                "confidence": 0.0,
                "provider": "google",
                "error": "Google STT API key not configured",
            }
        import base64

        lang = language or "en-US"
        payload = {
            "config": {
                "encoding": "LINEAR16",
                "languageCode": lang,
                "enableAutomaticPunctuation": True,
            },
            "audio": {"content": base64.b64encode(audio_bytes).decode("ascii")},
        }
        try:
            async with httpx.AsyncClient(timeout=120) as client:
                response = await client.post(
                    f"{self.base_url}/speech:recognize",
                    params={"key": self._credential},
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPStatusError as exc:
            logger.error(
                "Google STT error",
                extra={
                    "provider": "google",
                    "status_code": exc.response.status_code,
                    "error": exc.response.text[:200],
                },
            )
            raise ProviderError(
                f"Google STT error: {exc.response.status_code}"
            ) from exc
        except httpx.RequestError as exc:
            logger.error(
                "Google STT connection error",
                extra={"provider": "google", "error": str(exc)},
            )
            raise ProviderError(f"Google STT connection error: {exc}") from exc

        results = data.get("results", [])
        text = ""
        confidence = 0.0
        if results:
            alternative = results[0].get("alternatives", [{}])[0]
            text = alternative.get("transcript", "")
            confidence = float(alternative.get("confidence", 0.0) or 0.0)

        return {
            "text": text,
            "confidence": confidence,
            "provider": "google",
        }

    async def text_to_speech(
        self, *, text: str, voice: str | None = None, language: str | None = None
    ) -> dict[str, Any]:
        """Convert text to speech audio via Google Text-to-Speech."""
        if not self._credential:
            return {
                "audio_bytes": b"",
                "content_type": "audio/mpeg",
                "provider": "google",
                "error": "Google TTS API key not configured",
            }
        import base64

        lang = language or "en-US"
        voice_name = voice or "en-US-Standard-A"
        payload = {
            "input": {"text": text},
            "voice": {"languageCode": lang, "name": voice_name},
            "audioConfig": {"audioEncoding": "MP3"},
        }
        try:
            async with httpx.AsyncClient(timeout=120) as client:
                response = await client.post(
                    "https://texttospeech.googleapis.com/v1/text:synthesize",
                    params={"key": self._credential},
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPStatusError as exc:
            logger.error(
                "Google TTS error",
                extra={
                    "provider": "google",
                    "status_code": exc.response.status_code,
                    "error": exc.response.text[:200],
                },
            )
            raise ProviderError(
                f"Google TTS error: {exc.response.status_code}"
            ) from exc
        except httpx.RequestError as exc:
            logger.error(
                "Google TTS connection error",
                extra={"provider": "google", "error": str(exc)},
            )
            raise ProviderError(f"Google TTS connection error: {exc}") from exc

        audio_bytes = base64.b64decode(data.get("audioContent", ""))
        return {
            "audio_bytes": audio_bytes,
            "content_type": "audio/mpeg",
            "provider": "google",
        }


class AWSVoiceProvider(VoiceProvider):
    """Amazon Web Services provider for STT (Transcribe) and TTS (Polly).

    AWS request signing requires Signature Version 4, which is not
    implemented here to keep dependencies minimal and avoid embedding
    signing logic. When credentials are configured, calls return a clear
    not-implemented error rather than attempting unsigned requests.
    """

    def __init__(
        self,
        *,
        credential: str | None,
        base_url: str | None = None,
    ) -> None:
        self._credential = credential
        self.base_url = base_url or ""
        self._api_key_redacted = redact_secret(credential)

    async def speech_to_text(
        self, *, audio_bytes: bytes, language: str | None = None
    ) -> dict[str, Any]:
        return {
            "text": "",
            "confidence": 0.0,
            "provider": "aws",
            "error": "AWS Transcribe requires SigV4 signing (not implemented)",
        }

    async def text_to_speech(
        self, *, text: str, voice: str | None = None, language: str | None = None
    ) -> dict[str, Any]:
        return {
            "audio_bytes": b"",
            "content_type": "audio/mpeg",
            "provider": "aws",
            "error": "AWS Polly requires SigV4 signing (not implemented)",
        }


class NVIDIAVoiceProvider(VoiceProvider):
    """NVIDIA NIM provider for STT and TTS.

    Uses the NVIDIA NIM audio endpoints (OpenAI-compatible
    ``/audio/transcriptions`` and ``/audio/speech``) with Bearer-token
    authentication via the API key. No credentials are embedded.
    """

    def __init__(
        self,
        *,
        credential: str | None,
        base_url: str | None = None,
    ) -> None:
        self._credential = credential
        self.base_url = base_url or "https://integrate.api.nvidia.com/v1"
        self._api_key_redacted = redact_secret(credential)

    async def speech_to_text(
        self, *, audio_bytes: bytes, language: str | None = None
    ) -> dict[str, Any]:
        """Convert speech audio to text via NVIDIA NIM ASR."""
        if not self._credential:
            return {
                "text": "",
                "confidence": 0.0,
                "provider": "nvidia",
                "error": "NVIDIA NIM API key not configured",
            }
        headers = {
            "Authorization": f"Bearer {self._credential}",
            "Content-Type": "audio/wav",
        }
        data: dict[str, Any] = {}
        if language:
            data["language"] = language
        try:
            async with httpx.AsyncClient(timeout=120) as client:
                response = await client.post(
                    f"{self.base_url}/audio/transcriptions",
                    headers=headers,
                    data=data or None,
                    files={"file": ("audio.wav", audio_bytes, "audio/wav")},
                )
                response.raise_for_status()
                result = response.json()
        except httpx.HTTPStatusError as exc:
            logger.error(
                "NVIDIA NIM STT error",
                extra={
                    "provider": "nvidia",
                    "status_code": exc.response.status_code,
                    "error": exc.response.text[:200],
                },
            )
            raise ProviderError(
                f"NVIDIA NIM STT error: {exc.response.status_code}"
            ) from exc
        except httpx.RequestError as exc:
            logger.error(
                "NVIDIA NIM STT connection error",
                extra={"provider": "nvidia", "error": str(exc)},
            )
            raise ProviderError(f"NVIDIA NIM STT connection error: {exc}") from exc

        return {
            "text": result.get("text", ""),
            "confidence": float(result.get("confidence", 0.0) or 0.0),
            "provider": "nvidia",
        }

    async def text_to_speech(
        self, *, text: str, voice: str | None = None, language: str | None = None
    ) -> dict[str, Any]:
        """Convert text to speech audio via NVIDIA NIM TTS."""
        if not self._credential:
            return {
                "audio_bytes": b"",
                "content_type": "audio/mpeg",
                "provider": "nvidia",
                "error": "NVIDIA NIM API key not configured",
            }
        headers = {
            "Authorization": f"Bearer {self._credential}",
            "Content-Type": "application/json",
        }
        payload: dict[str, Any] = {
            "input": text,
        }
        if voice:
            payload["voice"] = voice
        if language:
            payload["language"] = language
        try:
            async with httpx.AsyncClient(timeout=120) as client:
                response = await client.post(
                    f"{self.base_url}/audio/speech",
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()
                audio_bytes = response.content
        except httpx.HTTPStatusError as exc:
            logger.error(
                "NVIDIA NIM TTS error",
                extra={
                    "provider": "nvidia",
                    "status_code": exc.response.status_code,
                    "error": exc.response.text[:200],
                },
            )
            raise ProviderError(
                f"NVIDIA NIM TTS error: {exc.response.status_code}"
            ) from exc
        except httpx.RequestError as exc:
            logger.error(
                "NVIDIA NIM TTS connection error",
                extra={"provider": "nvidia", "error": str(exc)},
            )
            raise ProviderError(f"NVIDIA NIM TTS connection error: {exc}") from exc

        return {
            "audio_bytes": audio_bytes,
            "content_type": "audio/mpeg",
            "provider": "nvidia",
        }


def _build_provider(
    *,
    stt_provider: str,
    stt_api_key: str | None,
    stt_api_url: str | None,
    tts_provider: str,
    tts_api_key: str | None,
    tts_api_url: str | None,
) -> VoiceProvider:
    """Select and build the voice provider from configuration.

    STT and TTS may use different providers; the returned provider handles
    both directions. When a cloud provider is configured without an API key,
    the LocalVoiceProvider stub is used so the system stays functional.
    """

    def provider_for(
        name: str, api_key: str | None, api_url: str | None
    ) -> VoiceProvider:
        if name == "azure":
            return AzureVoiceProvider(credential=api_key, base_url=api_url)
        if name == "google":
            return GoogleVoiceProvider(credential=api_key, base_url=api_url)
        if name == "aws":
            return AWSVoiceProvider(credential=api_key, base_url=api_url)
        if name == "nvidia":
            return NVIDIAVoiceProvider(credential=api_key, base_url=api_url)
        if name == "local":
            return LocalVoiceProvider()
        logger.warning("Unknown voice provider '%s', falling back to local stub", name)
        return LocalVoiceProvider()

    # Only use a cloud provider when both directions point at the same
    # configured cloud provider AND both API keys are present. Otherwise
    # fall back to the local stub so no credentials are silently assumed
    # and partial configuration cannot silently route audio to a cloud.
    stt = provider_for(stt_provider, stt_api_key, stt_api_url)
    tts = provider_for(tts_provider, tts_api_key, tts_api_url)
    if (
        type(stt) is type(tts)
        and not isinstance(stt, LocalVoiceProvider)
        and stt_api_key
        and tts_api_key
    ):
        return stt
    return LocalVoiceProvider()


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
    provider=_build_provider(
        stt_provider=settings.voice_stt_provider,
        stt_api_key=settings.voice_stt_api_key,
        stt_api_url=settings.voice_stt_api_url,
        tts_provider=settings.voice_tts_provider,
        tts_api_key=settings.voice_tts_api_key,
        tts_api_url=settings.voice_tts_api_url,
    ),
    enabled=settings.voice_enabled,
)
