"""Vision API endpoints.

Provides image understanding operations.
Gated behind the vision_enabled configuration flag and execution-time
policy enforcement.
"""

from __future__ import annotations

import base64
import time

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from jarvis.ai.vision import validate_image, vision
from jarvis.api.auth import get_current_user
from jarvis.auth import require_policy
from jarvis.core.config import settings
from jarvis.core.logging import get_logger
from jarvis.core.metrics import record_vision_request
from jarvis.core.security import Permission
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


def _decode_image(image_b64: str) -> bytes:
    try:
        return base64.b64decode(image_b64, validate=True)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid base64 image data",
        ) from exc


@router.post(
    "/describe",
    response_model=DescribeImageResponse,
    dependencies=[
        Depends(
            require_policy(
                required_permission=Permission.VISION_READ,
                action="describe image",
                risk_level="low",
            )
        )
    ],
)
async def describe_image(
    request: DescribeImageRequest,
    session: AsyncSession = Depends(get_session),  # noqa: B008
    authorization: str | None = None,
) -> DescribeImageResponse:
    """Describe or analyze an image."""
    if not settings.vision_enabled:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Vision interface is disabled. Set JARVIS_VISION_ENABLED=true to enable.",
        )
    await get_current_user(session, authorization)
    image_bytes = _decode_image(request.image_b64)
    validate_image(image_bytes)
    start = time.time()
    outcome = "success"
    try:
        result = await vision.describe_image(
            image_bytes=image_bytes, prompt=request.prompt
        )
        return DescribeImageResponse(
            description=result.get("description", ""),
            confidence=result.get("confidence", 0.0),
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
        record_vision_request(
            operation="describe",
            provider=getattr(
                vision.provider, "__class__", type(vision.provider)
            ).__name__.lower(),
            outcome=outcome,
            duration=duration,
            image_bytes=len(image_bytes),
        )


@router.post(
    "/analyze",
    response_model=AnalyzeImageResponse,
    dependencies=[
        Depends(
            require_policy(
                required_permission=Permission.VISION_READ,
                action="analyze image",
                risk_level="low",
            )
        )
    ],
)
async def analyze_image(
    request: AnalyzeImageRequest,
    session: AsyncSession = Depends(get_session),  # noqa: B008
    authorization: str | None = None,
) -> AnalyzeImageResponse:
    """Answer questions about an image."""
    if not settings.vision_enabled:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Vision interface is disabled. Set JARVIS_VISION_ENABLED=true to enable.",
        )
    await get_current_user(session, authorization)
    image_bytes = _decode_image(request.image_b64)
    validate_image(image_bytes)
    start = time.time()
    outcome = "success"
    try:
        result = await vision.analyze_image(
            image_bytes=image_bytes, questions=request.questions
        )
        return AnalyzeImageResponse(
            answers=result.get("answers", {}),
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
        record_vision_request(
            operation="analyze",
            provider=getattr(
                vision.provider, "__class__", type(vision.provider)
            ).__name__.lower(),
            outcome=outcome,
            duration=duration,
            image_bytes=len(image_bytes),
        )
