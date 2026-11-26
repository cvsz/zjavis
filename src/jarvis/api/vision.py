"""Vision API endpoints.

Provides image understanding operations.
Gated behind the vision_enabled configuration flag.
"""

from __future__ import annotations

import base64

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from jarvis.ai.vision import vision
from jarvis.api.auth import get_current_user
from jarvis.core.logging import get_logger
from jarvis.db import get_session

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/vision", tags=["vision"])


class DescribeImageRequest(BaseModel):
    image_b64: str = Field(..., description="Base64-encoded image data")
    prompt: str | None = Field(default=None, max_length=1000)


class DescribeImageResponse(BaseModel):
    description: str
    confidence: float
    provider: str


class AnalyzeImageRequest(BaseModel):
    image_b64: str = Field(..., description="Base64-encoded image data")
    questions: list[str] = Field(..., min_length=1, max_length=10)


class AnalyzeImageResponse(BaseModel):
    answers: dict[str, str]
    provider: str


@router.post("/describe", response_model=DescribeImageResponse)
async def describe_image(
    request: DescribeImageRequest,
    session: AsyncSession = Depends(get_session),  # noqa: B008
    authorization: str | None = None,
) -> DescribeImageResponse:
    """Describe or analyze an image."""
    await get_current_user(session, authorization)
    image_bytes = base64.b64decode(request.image_b64)
    result = await vision.describe_image(image_bytes=image_bytes, prompt=request.prompt)
    if "error" in result:
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=result["error"])
    return DescribeImageResponse(
        description=result.get("description", ""),
        confidence=result.get("confidence", 0.0),
        provider=result.get("provider", "unknown"),
    )


@router.post("/analyze", response_model=AnalyzeImageResponse)
async def analyze_image(
    request: AnalyzeImageRequest,
    session: AsyncSession = Depends(get_session),  # noqa: B008
    authorization: str | None = None,
) -> AnalyzeImageResponse:
    """Answer questions about an image."""
    await get_current_user(session, authorization)
    image_bytes = base64.b64decode(request.image_b64)
    result = await vision.analyze_image(image_bytes=image_bytes, questions=request.questions)
    if "error" in result:
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=result["error"])
    return AnalyzeImageResponse(
        answers=result.get("answers", {}),
        provider=result.get("provider", "unknown"),
    )
