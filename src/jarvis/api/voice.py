"""Voice API endpoints.

Provides speech-to-text and text-to-speech operations.
Gated behind the voice_enabled configuration flag and execution-time
policy enforcement.
"""

from __future__ import annotations

import base64
import time

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from jarvis.ai.voice import validate_audio, voice
from jarvis.api.auth import get_current_user
from jarvis.auth import require_policy
from jarvis.core.config import settings
from jarvis.core.logging import get_logger
from jarvis.core.metrics import record_voice_request
from jarvis.core.security import Permission
from jarvis.db import get_session

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/voice", tags=["voice"])


class SpeechToTextRequest(BaseModel):
    audio_b64: str = Field(..., description="Base64-encoded audio data")
    language: str | None = Field(default=None, max_length=10)


class SpeechToTextResponse(BaseModel):
    text: str
    confidence: float
    provider: str


class TextToSpeechRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=4000)
    voice: str | None = Field(default=None, max_length=50)
    language: str | None = Field(default=None, max_length=10)


class TextToSpeechResponse(BaseModel):
    audio_b64: str
    content_type: str
    provider: str


@router.post(
    "/speech-to-text",
    response_model=SpeechToTextResponse,
    dependencies=[
        Depends(
            require_policy(
                required_permission=Permission.VOICE_READ,
                action="speech-to-text",
                risk_level="low",
            )
        )
    ],
)
async def speech_to_text(
    request: SpeechToTextRequest,
    session: AsyncSession = Depends(get_session),  # noqa: B008
    authorization: str | None = None,
) -> SpeechToTextResponse:
    """Convert speech audio to text."""
    if not settings.voice_enabled:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Voice interface is disabled. Set JARVIS_VOICE_ENABLED=true to enable.",
        )
    await get_current_user(session, authorization)
    try:
        audio_bytes = base64.b64decode(request.audio_b64)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid base64 audio data",
        ) from exc
    validate_audio(audio_bytes)
    start = time.time()
    outcome = "success"
    try:
        result = await voice.speech_to_text(
            audio_bytes=audio_bytes, language=request.language
        )
        return SpeechToTextResponse(
            text=result.get("text", ""),
            confidence=result.get("confidence", 0.0),
            provider=result.get("provider", "unknown"),
        )
    except Exception:
        outcome = "error"
        raise
    finally:
        duration = time.time() - start
        record_voice_request(
            operation="stt",
            provider=getattr(
                voice.provider, "__class__", type(voice.provider)
            ).__name__.lower(),
            outcome=outcome,
            duration=duration,
            audio_bytes=len(audio_bytes),
        )


@router.post(
    "/text-to-speech",
    response_model=TextToSpeechResponse,
    dependencies=[
        Depends(
            require_policy(
                required_permission=Permission.VOICE_WRITE,
                action="text-to-speech",
                risk_level="low",
            )
        )
    ],
)
async def text_to_speech(
    request: TextToSpeechRequest,
    session: AsyncSession = Depends(get_session),  # noqa: B008
    authorization: str | None = None,
) -> TextToSpeechResponse:
    """Convert text to speech audio."""
    if not settings.voice_enabled:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Voice interface is disabled. Set JARVIS_VOICE_ENABLED=true to enable.",
        )
    await get_current_user(session, authorization)
    start = time.time()
    outcome = "success"
    try:
        result = await voice.text_to_speech(
            text=request.text, voice=request.voice, language=request.language
        )
        if "error" in result:
            outcome = "error"
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=result["error"]
            )
        audio_b64 = base64.b64encode(result.get("audio_bytes", b"")).decode("ascii")
        return TextToSpeechResponse(
            audio_b64=audio_b64,
            content_type=result.get("content_type", "audio/wav"),
            provider=result.get("provider", "unknown"),
        )
    except HTTPException:
        outcome = "error"
        raise
    except Exception:
        outcome = "error"
        raise
    finally:
        duration = time.time() - start
        record_voice_request(
            operation="tts",
            provider=getattr(
                voice.provider, "__class__", type(voice.provider)
            ).__name__.lower(),
            outcome=outcome,
            duration=duration,
            audio_bytes=0,
        )
