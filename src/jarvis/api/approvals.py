"""Approval API endpoints.

Provides approval request lifecycle management with tenant isolation.
Integrates with the ApprovalService for business logic.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from jarvis.api.auth import get_current_user
from jarvis.approval import ApprovalService
from jarvis.core.logging import get_logger
from jarvis.db import get_session
from jarvis.db.models import Approval

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/approvals", tags=["approvals"])


class ApprovalRequest(BaseModel):
    task_id: UUID
    expires_in_minutes: int = Field(default=60, ge=1, le=10080)


class ApprovalResponse(BaseModel):
    id: str
    task_id: str
    requested_by: str
    approved_by: str | None
    state: str
    expires_at: str | None


@router.post("", response_model=ApprovalResponse, status_code=status.HTTP_201_CREATED)
async def request_approval(
    request: ApprovalRequest,
    session: AsyncSession = Depends(get_session),  # noqa: B008
    authorization: str | None = None,
) -> ApprovalResponse:
    """Request approval for a consequential action."""
    user = await get_current_user(session, authorization)
    service = ApprovalService(session)
    approval = await service.request_approval(
        task_id=request.task_id,
        requested_by=UUID(str(user.id)),
        expires_in_minutes=request.expires_in_minutes,
    )
    return ApprovalResponse(
        id=str(approval.id),
        task_id=str(approval.task_id),
        requested_by=str(approval.requested_by),
        approved_by=str(approval.approved_by) if approval.approved_by else None,
        state=approval.state,  # type: ignore[arg-type]
        expires_at=str(approval.expires_at) if approval.expires_at else None,
    )


@router.get("", response_model=list[ApprovalResponse])
async def list_approvals(
    session: AsyncSession = Depends(get_session),  # noqa: B008
    authorization: str | None = None,
    state: str | None = None,
    limit: int = 50,
) -> list[ApprovalResponse]:
    """List approvals for the authenticated user."""
    user = await get_current_user(session, authorization)
    query = select(Approval).where(Approval.requested_by == str(user.id))
    if state is not None:
        query = query.where(Approval.state == state)
    query = query.limit(limit)
    result = await session.execute(query)
    approvals = result.scalars().all()
    return [
        ApprovalResponse(
            id=str(a.id),
            task_id=str(a.task_id),
            requested_by=str(a.requested_by),
            approved_by=str(a.approved_by) if a.approved_by else None,
            state=a.state,  # type: ignore[arg-type]
            expires_at=str(a.expires_at) if a.expires_at else None,
        )
        for a in approvals
    ]


@router.get("/{approval_id}", response_model=ApprovalResponse)
async def get_approval(
    approval_id: UUID,
    session: AsyncSession = Depends(get_session),  # noqa: B008
    authorization: str | None = None,
) -> ApprovalResponse:
    """Get a single approval by ID."""
    await get_current_user(session, authorization)
    service = ApprovalService(session)
    approval = await service.get_approval(approval_id)
    return ApprovalResponse(
        id=str(approval.id),
        task_id=str(approval.task_id),
        requested_by=str(approval.requested_by),
        approved_by=str(approval.approved_by) if approval.approved_by else None,
        state=approval.state,  # type: ignore[arg-type]
        expires_at=str(approval.expires_at) if approval.expires_at else None,
    )


@router.post("/{approval_id}/grant", response_model=ApprovalResponse)
async def grant_approval(
    approval_id: UUID,
    session: AsyncSession = Depends(get_session),  # noqa: B008
    authorization: str | None = None,
) -> ApprovalResponse:
    """Grant a pending approval."""
    user = await get_current_user(session, authorization)
    service = ApprovalService(session)
    approval = await service.grant_approval(approval_id, UUID(str(user.id)))
    return ApprovalResponse(
        id=str(approval.id),
        task_id=str(approval.task_id),
        requested_by=str(approval.requested_by),
        approved_by=str(approval.approved_by) if approval.approved_by else None,
        state=approval.state,  # type: ignore[arg-type]
        expires_at=str(approval.expires_at) if approval.expires_at else None,
    )


@router.post("/{approval_id}/deny", response_model=ApprovalResponse)
async def deny_approval(
    approval_id: UUID,
    session: AsyncSession = Depends(get_session),  # noqa: B008
    authorization: str | None = None,
) -> ApprovalResponse:
    """Deny a pending approval."""
    user = await get_current_user(session, authorization)
    service = ApprovalService(session)
    approval = await service.deny_approval(approval_id, UUID(str(user.id)))
    return ApprovalResponse(
        id=str(approval.id),
        task_id=str(approval.task_id),
        requested_by=str(approval.requested_by),
        approved_by=str(approval.approved_by) if approval.approved_by else None,
        state=approval.state,  # type: ignore[arg-type]
        expires_at=str(approval.expires_at) if approval.expires_at else None,
    )
