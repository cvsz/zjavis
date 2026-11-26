"""Approval service: manages pending approvals for consequential actions.

Per javis-blueprint.md section 15.3, consequential actions require
explicit operator approval at execution time. Approvals are persisted
and have a lifecycle: pending -> granted/denied/expired.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from jarvis.core.exceptions import AuthorizationError, NotFoundError
from jarvis.core.logging import get_logger
from jarvis.db.models import Approval

logger = get_logger(__name__)


class ApprovalService:
    """Creates, retrieves, and resolves approval requests."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def request_approval(
        self,
        *,
        task_id: UUID,
        requested_by: UUID,
        expires_in_minutes: int = 60,
    ) -> Approval:
        """Create a pending approval request.

        Args:
            task_id: The task requiring approval.
            requested_by: The user requesting the approval.
            expires_in_minutes: Minutes until the approval expires.

        Returns:
            The created :class:`Approval` record.
        """
        expires_at = datetime.now(UTC) + timedelta(
            minutes=expires_in_minutes
        )
        approval = Approval(
            task_id=task_id,
            requested_by=requested_by,
            state="pending",
            expires_at=expires_at,
        )
        self.session.add(approval)
        await self.session.commit()
        await self.session.refresh(approval)
        logger.info(
            "Approval requested",
            extra={
                "approval_id": str(approval.id),
                "task_id": str(task_id),
                "requested_by": str(requested_by),
                "expires_at": expires_at.isoformat(),
            },
        )
        return approval

    async def get_approval(self, approval_id: UUID) -> Approval:
        """Retrieve an approval by ID.

        Raises:
            NotFoundError: If the approval does not exist.
        """
        result = await self.session.execute(
            select(Approval).where(Approval.id == approval_id)
        )
        approval = result.scalar_one_or_none()
        if approval is None:
            raise NotFoundError(f"Approval not found: {approval_id}")
        return approval

    async def grant_approval(
        self, approval_id: UUID, approved_by: UUID
    ) -> Approval:
        """Grant a pending approval.

        Args:
            approval_id: The approval to grant.
            approved_by: The user granting the approval.

        Returns:
            The updated :class:`Approval`.

        Raises:
            NotFoundError: If the approval does not exist.
            AuthorizationError: If the approval is not in pending state.
        """
        approval = await self.get_approval(approval_id)
        if approval.state != "pending":
            raise AuthorizationError(
                f"Approval is not pending (current state: {approval.state})",
                code="invalid_approval_state",
            )
        approval.state = "granted"  # type: ignore[assignment]
        approval.approved_by = approved_by  # type: ignore[assignment]
        await self.session.commit()
        await self.session.refresh(approval)
        logger.info(
            "Approval granted",
            extra={
                "approval_id": str(approval_id),
                "approved_by": str(approved_by),
            },
        )
        return approval

    async def deny_approval(
        self, approval_id: UUID, approved_by: UUID
    ) -> Approval:
        """Deny a pending approval.

        Args:
            approval_id: The approval to deny.
            approved_by: The user denying the approval.

        Returns:
            The updated :class:`Approval`.
        """
        approval = await self.get_approval(approval_id)
        if approval.state != "pending":
            raise AuthorizationError(
                f"Approval is not pending (current state: {approval.state})",
                code="invalid_approval_state",
            )
        approval.state = "denied"  # type: ignore[assignment]
        approval.approved_by = approved_by  # type: ignore[assignment]
        await self.session.commit()
        await self.session.refresh(approval)
        logger.info(
            "Approval denied",
            extra={
                "approval_id": str(approval_id),
                "approved_by": str(approved_by),
            },
        )
        return approval

    async def expire_approvals(self) -> int:
        """Expire all pending approvals past their expiration time.

        Returns:
            The number of approvals expired.
        """
        now = datetime.now(UTC)
        result = await self.session.execute(
            select(Approval).where(
                Approval.state == "pending",
                Approval.expires_at < now,  # type: ignore[arg-type]
            )
        )
        expired = result.scalars().all()
        for approval in expired:
            approval.state = "expired"  # type: ignore[assignment]
        if expired:
            await self.session.commit()
        logger.info("Expired %d pending approvals", len(expired))
        return len(expired)

    async def is_approved(self, task_id: UUID) -> bool:
        """Check whether a task has an active granted approval.

        Args:
            task_id: The task to check.

        Returns:
            True if a granted, non-expired approval exists.
        """
        now = datetime.now(UTC)
        result = await self.session.execute(
            select(Approval).where(
                Approval.task_id == task_id,
                Approval.state == "granted",
                Approval.expires_at > now,  # type: ignore[arg-type]
            )
        )
        return result.scalar_one_or_none() is not None
