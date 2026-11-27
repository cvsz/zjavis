"""Audit API endpoints.

Provides audit event retrieval with tenant isolation.
Integrates with the AuditService for business logic.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from jarvis.api.auth import get_current_user
from jarvis.audit import AuditService
from jarvis.core.logging import get_logger
from jarvis.db import get_session

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/audit", tags=["audit"])


class AuditEventResponse(BaseModel):
    id: str
    tenant_id: str
    actor_id: str | None
    event_type: str
    event_category: str
    outcome: str
    details: str | None
    occurred_at: str


@router.get("/events", response_model=list[AuditEventResponse])
async def list_audit_events(
    session: AsyncSession = Depends(get_session),  # noqa: B008
    authorization: str | None = None,
    event_type: str | None = None,
    event_category: str | None = None,
    limit: int = 100,
) -> list[AuditEventResponse]:
    """List audit events for the authenticated user's tenant."""
    user = await get_current_user(session, authorization)
    tenant_id = user.tenant_id
    if tenant_id is None:
        tenant_id = user.organization_id
    service = AuditService(session)
    events = await service.get_events(
        tenant_id=tenant_id,
        event_type=event_type,
        event_category=event_category,
        limit=limit,
    )
    return [
        AuditEventResponse(
            id=str(e.id),
            tenant_id=str(e.tenant_id),
            actor_id=str(e.actor_id) if e.actor_id else None,
            event_type=e.event_type,
            event_category=e.event_category,
            outcome=e.outcome,
            details=e.details,
            occurred_at=str(e.occurred_at),
        )
        for e in events
    ]
