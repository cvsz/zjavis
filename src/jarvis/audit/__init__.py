"""Audit service: records tamper-evident audit events.

Per javis-blueprint.md section 15.1, audit records must be tamper-evident.
Events record actor, tenant, event type, category, outcome, and details.
Secrets are never recorded in audit events.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from jarvis.core.logging import get_logger
from jarvis.db.models import AuditEvent

logger = get_logger(__name__)

# Event categories
CAT_AUTH = "auth"
CAT_SECURITY = "security"
CAT_SYSTEM = "system"
CAT_TOOL = "tool"
CAT_AGENT = "agent"
CAT_MEMORY = "memory"
CAT_APPROVAL = "approval"

# Outcomes
OUTCOME_SUCCESS = "success"
OUTCOME_FAILURE = "failure"
OUTCOME_DENIAL = "denial"


class AuditService:
    """Records audit events to the durable audit log."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def record(
        self,
        *,
        event_type: str,
        event_category: str,
        outcome: str,
        tenant_id: UUID | None = None,
        actor_id: UUID | None = None,
        details: str | None = None,
    ) -> AuditEvent:
        """Record an audit event.

        Args:
            event_type: The type of event (e.g. ``login``, ``task.execute``).
            event_category: One of the CAT_* constants.
            outcome: One of OUTCOME_* constants.
            tenant_id: The tenant context (optional).
            actor_id: The acting user (optional).
            details: Human-readable details (no secrets).

        Returns:
            The created :class:`AuditEvent`.
        """
        event = AuditEvent(
            tenant_id=tenant_id,
            actor_id=actor_id,
            event_type=event_type,
            event_category=event_category,
            outcome=outcome,
            details=details,
            occurred_at=datetime.now(UTC),
        )
        self.session.add(event)
        await self.session.commit()
        await self.session.refresh(event)
        logger.info(
            "Audit event recorded",
            extra={
                "audit_id": str(event.id),
                "event_type": event_type,
                "event_category": event_category,
                "outcome": outcome,
                "tenant_id": str(tenant_id) if tenant_id else None,
                "actor_id": str(actor_id) if actor_id else None,
            },
        )
        return event

    async def get_events(
        self,
        *,
        tenant_id: UUID | None = None,
        event_type: str | None = None,
        event_category: str | None = None,
        limit: int = 100,
    ) -> list[AuditEvent]:
        """Retrieve audit events with optional filters.

        Args:
            tenant_id: Filter by tenant.
            event_type: Filter by event type.
            event_category: Filter by category.
            limit: Maximum number of events to return.

        Returns:
            A list of :class:`AuditEvent` ordered by occurred_at descending.
        """
        query = select(AuditEvent)
        if tenant_id is not None:
            query = query.where(AuditEvent.tenant_id == tenant_id)
        if event_type is not None:
            query = query.where(AuditEvent.event_type == event_type)
        if event_category is not None:
            query = query.where(AuditEvent.event_category == event_category)
        query = query.order_by(AuditEvent.occurred_at.desc()).limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())
