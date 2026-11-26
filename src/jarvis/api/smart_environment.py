"""Smart Environment API endpoints.

Provides IoT device management operations.
Gated behind the smart_environment_enabled configuration flag.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from jarvis.ai.smart_environment import smart_environment
from jarvis.api.auth import get_current_user
from jarvis.core.logging import get_logger
from jarvis.db import get_session

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/smart-environment", tags=["smart-environment"])


class DeviceStateRequest(BaseModel):
    state: dict[str, str]


class DeviceListResponse(BaseModel):
    devices: list[dict[str, object]]


class DeviceStateResponse(BaseModel):
    device_id: str
    state: dict[str, object]


@router.get("/devices", response_model=DeviceListResponse)
async def list_devices(
    session: AsyncSession = Depends(get_session),  # noqa: B008
    authorization: str | None = None,
) -> DeviceListResponse:
    """List all available smart environment devices."""
    await get_current_user(session, authorization)
    devices = await smart_environment.list_devices()
    return DeviceListResponse(devices=devices)


@router.get("/devices/{device_id}/state", response_model=DeviceStateResponse)
async def get_device_state(
    device_id: str,
    session: AsyncSession = Depends(get_session),  # noqa: B008
    authorization: str | None = None,
) -> DeviceStateResponse:
    """Get the current state of a device."""
    await get_current_user(session, authorization)
    result = await smart_environment.get_device_state(device_id)
    if "error" in result:
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=result["error"])
    return DeviceStateResponse(
        device_id=result.get("device_id", device_id),
        state=result.get("state", {}),
    )


@router.post("/devices/{device_id}/state", response_model=DeviceStateResponse)
async def set_device_state(
    device_id: str,
    request: DeviceStateRequest,
    session: AsyncSession = Depends(get_session),  # noqa: B008
    authorization: str | None = None,
) -> DeviceStateResponse:
    """Set the state of a device."""
    await get_current_user(session, authorization)
    result = await smart_environment.set_device_state(device_id, request.state)
    if "error" in result:
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=result["error"])
    return DeviceStateResponse(
        device_id=result.get("device_id", device_id),
        state=result.get("state", {}),
    )
