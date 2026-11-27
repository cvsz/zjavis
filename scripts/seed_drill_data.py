"""Seed minimal data into every JARVIS core table for a restore drill.

Inserts a small, consistent graph covering all 14 core entities so a
backup/restore drill can verify that data (not just schema) is preserved
across a restore. Safe to re-run: uses idempotent lookups and only inserts
when rows are missing.
"""

from __future__ import annotations

import asyncio
from datetime import UTC

from sqlalchemy import select

from jarvis.db.models import (
    Agent,
    Approval,
    AuditEvent,
    Conversation,
    Memory,
    Message,
    Organization,
    Permission,
    Role,
    RoleBinding,
    RolePermission,
    Session,
    Task,
    Tenant,
    User,
)
from jarvis.db.session import async_session

ORG_NAME = "Drill Org"
ORG_SLUG = "drill-org"
USER_EMAIL = "drill@example.com"
USER_USERNAME = "drilluser"
TENANT_NAME = "Drill Tenant"
TENANT_SLUG = "drill-tenant"
ROLE_NAME = "drill-role"
PERM_NAME = "drill:read"


async def seed() -> None:
    async with async_session() as session:
        # Organization
        org = (
            await session.execute(
                select(Organization).where(Organization.slug == ORG_SLUG)
            )
        ).scalar_one_or_none()
        if org is None:
            org = Organization(name=ORG_NAME, slug=ORG_SLUG, is_active=True)
            session.add(org)
            await session.flush()

        # User
        user = (
            await session.execute(select(User).where(User.email == USER_EMAIL))
        ).scalar_one_or_none()
        if user is None:
            import hashlib

            pw_hash = hashlib.pbkdf2_hmac(
                "sha256", b"drill-password", b"drill-salt", 210000
            ).hex()
            user = User(
                organization_id=org.id,
                email=USER_EMAIL,
                username=USER_USERNAME,
                password_hash=pw_hash,
                is_active=True,
            )
            session.add(user)
            await session.flush()

        # Tenant
        tenant = (
            await session.execute(select(Tenant).where(Tenant.slug == TENANT_SLUG))
        ).scalar_one_or_none()
        if tenant is None:
            tenant = Tenant(
                organization_id=org.id,
                name=TENANT_NAME,
                slug=TENANT_SLUG,
                is_active=True,
            )
            session.add(tenant)
            await session.flush()

        # Role
        role = (
            await session.execute(select(Role).where(Role.name == ROLE_NAME))
        ).scalar_one_or_none()
        if role is None:
            role = Role(name=ROLE_NAME, description="Drill role")
            session.add(role)
            await session.flush()

        # Permission
        perm = (
            await session.execute(
                select(Permission).where(Permission.name == PERM_NAME)
            )
        ).scalar_one_or_none()
        if perm is None:
            perm = Permission(name=PERM_NAME, description="Drill permission")
            session.add(perm)
            await session.flush()

        # RolePermission
        rp = (
            await session.execute(
                select(RolePermission).where(
                    RolePermission.role_id == role.id,
                    RolePermission.permission_id == perm.id,
                )
            )
        ).scalar_one_or_none()
        if rp is None:
            session.add(RolePermission(role_id=role.id, permission_id=perm.id))

        # RoleBinding
        rb = (
            await session.execute(
                select(RoleBinding).where(
                    RoleBinding.user_id == user.id,
                    RoleBinding.role_id == role.id,
                    RoleBinding.tenant_id == tenant.id,
                )
            )
        ).scalar_one_or_none()
        if rb is None:
            session.add(
                RoleBinding(user_id=user.id, role_id=role.id, tenant_id=tenant.id)
            )

        # Session
        sess = (
            await session.execute(select(Session).where(Session.user_id == user.id))
        ).scalar_one_or_none()
        if sess is None:
            from datetime import datetime, timedelta

            session.add(
                Session(
                    user_id=user.id,
                    tenant_id=tenant.id,
                    token_hash="drill-token-hash",
                    expires_at=datetime.now(UTC) + timedelta(days=7),
                    is_revoked=False,
                )
            )

        # Conversation
        conv = (
            await session.execute(
                select(Conversation).where(Conversation.tenant_id == tenant.id)
            )
        ).scalar_one_or_none()
        if conv is None:
            conv = Conversation(
                tenant_id=tenant.id,
                user_id=user.id,
                title="Drill conversation",
            )
            session.add(conv)
            await session.flush()

        # Message
        msg = (
            await session.execute(
                select(Message).where(Message.conversation_id == conv.id)
            )
        ).scalar_one_or_none()
        if msg is None:
            session.add(
                Message(
                    conversation_id=conv.id,
                    role="user",
                    content="Drill message",
                    token_count=2,
                )
            )

        # Memory
        mem = (
            await session.execute(select(Memory).where(Memory.tenant_id == tenant.id))
        ).scalar_one_or_none()
        if mem is None:
            session.add(
                Memory(
                    tenant_id=tenant.id,
                    user_id=user.id,
                    memory_type="working",
                    content="Drill memory content",
                    source="drill",
                )
            )

        # Agent
        agent = (
            await session.execute(select(Agent).where(Agent.tenant_id == tenant.id))
        ).scalar_one_or_none()
        if agent is None:
            agent = Agent(
                tenant_id=tenant.id,
                name="Drill Agent",
                is_active=True,
            )
            session.add(agent)
            await session.flush()

        # Task
        task = (
            await session.execute(select(Task).where(Task.tenant_id == tenant.id))
        ).scalar_one_or_none()
        if task is None:
            task = Task(
                tenant_id=tenant.id,
                user_id=user.id,
                agent_id=agent.id,
                task_type="drill-task",
                risk_classification="low",
                state="queued",
            )
            session.add(task)
            await session.flush()

        # Approval
        appr = (
            await session.execute(select(Approval).where(Approval.task_id == task.id))
        ).scalar_one_or_none()
        if appr is None:
            session.add(
                Approval(
                    task_id=task.id,
                    requested_by=user.id,
                    state="pending",
                )
            )

        # AuditEvent
        audit = (
            await session.execute(
                select(AuditEvent).where(AuditEvent.tenant_id == tenant.id)
            )
        ).scalar_one_or_none()
        if audit is None:
            session.add(
                AuditEvent(
                    tenant_id=tenant.id,
                    actor_id=user.id,
                    event_type="drill.event",
                    event_category="system",
                    outcome="success",
                    details="Drill audit event",
                )
            )

        await session.commit()
        print("==> Seed complete: minimal data present in all 14 core tables")


def main() -> None:
    asyncio.run(seed())


if __name__ == "__main__":
    main()
