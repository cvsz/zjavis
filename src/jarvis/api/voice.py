"""Voice API endpoints.

Provides speech-to-text and text-to-speech operations.
Gated behind the voice_enabled configuration flag.
"""

from __future__ import annotations

import base64

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from jarvis.ai.voice import voice
from jarvis.api.auth import get_current_user
from jarvis.core.logging import get_logger
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


@router.post("/speech-to-text", response_model=SpeechToTextResponse)
async def speech_to_text(
    request: SpeechToTextRequest,
    session: AsyncSession = Depends(get_session),  # noqa: B008
    authorization: str | None = None,
) -> SpeechToTextResponse:
    """Convert speech audio to text."""
    await get_current_user(session, authorization)
    audio_bytes = base64.b64decode(request.audio_b64)
    result = await voice.speech_to_text(
        audio_bytes=audio_bytes, language=request.language
    )
    if "error" in result:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=result["error"]
        )
    return SpeechToTextResponse(
        text=result.get("text", ""),
        confidence=result.get("confidence", 0.0),
        provider=result.get("provider", "unknown"),
    )


@router.post("/text-to-speech", response_model=TextToSpeechResponse)
async def text_to_speech(
    request: TextToSpeechRequest,
    session: AsyncSession = Depends(get_session),  # noqa: B008
    authorization: str | None = None,
) -> TextToSpeechResponse:
    """Convert text to speech audio."""
    await get_current_user(session, authorization)
    result = await voice.text_to_speech(
        text=request.text, voice=request.voice, language=request.language
    )
    if "error" in result:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=result["error"]
        )
    audio_b64 = base64.b64encode(result.get("audio_bytes", b"")).decode("ascii")
    return TextToSpeechResponse(
        audio_b64=audio_b64,
        content_type=result.get("content_type", "audio/wav"),
        provider=result.get("provider", "unknown"),
    )
