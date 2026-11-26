"""Health endpoints for readiness and liveness probes.

Per javis-blueprint.md section 16.2, health and readiness probes must be
available so orchestrators can determine if the application and its
dependencies are usable.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from jarvis.core.logging import get_logger
from jarvis.db import get_session

logger = get_logger(__name__)

router = APIRouter(tags=["health"])


@router.get("/health", summary="Liveness probe")
async def health() -> dict[str, Any]:
    """Liveness probe: indicates the application process is alive.

    This endpoint does not check dependencies. It returns immediately
    if the process can respond.
    """
    return {"status": "alive", "service": "jarvis"}


@router.get("/ready", summary="Readiness probe")
async def ready(
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Readiness probe: indicates the application and dependencies are ready.

    Checks database connectivity by executing a trivial query. Returns
    503 if the database is unreachable.

    Returns:
        A dict with dependency health status.
    """
    checks: dict[str, Any] = {}
    overall = "ready"

    # Database check
    try:
        await session.execute(text("SELECT 1"))
        checks["database"] = {
            "status": "up",
            "detail": "SELECT 1 succeeded",
        }
    except Exception as exc:  # noqa: BLE001 - readiness probe reports failures
        logger.error("Database readiness check failed", extra={"error": str(exc)})
        checks["database"] = {
            "status": "down",
            "detail": "database unreachable",
        }
        overall = "not_ready"

    if overall != "ready":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"status": overall, "checks": checks},
        )

    return {"status": "ready", "service": "jarvis", "checks": checks}
