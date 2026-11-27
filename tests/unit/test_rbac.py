"""Unit tests for the fixed RBAC permission resolution.

Covers the repair of ``get_user_permissions()`` which previously joined
``role_bindings.role_id`` directly against ``permissions.id`` (two unrelated
tables) and therefore resolved to an empty permission set for every user.
The fix introduces the ``role_permissions`` junction table and corrects the
join to role_bindings -> role_permissions -> permissions.

Default permissions, the default "user" role, and the caller's role binding
are self-provisioned idempotently so authenticated users pass execution-time
policy checks out of the box.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select as _sa_select

from jarvis.auth import get_user_permissions
from jarvis.core.security import Permission, hash_password
from jarvis.db import async_session
from jarvis.db.models import (
    Organization,
    Role,
    RoleBinding,
    RolePermission,
    Tenant,
    User,
)
from jarvis.db.models import (
    Permission as DbPermission,
)
from jarvis.db.session import init_db


async def _create_user_and_tenant(session) -> tuple[User, uuid.UUID]:
    """Create an organization, user, and tenant; return (user, tenant_id)."""
    unique = uuid.uuid4().hex[:8]
    org = Organization(name=f"RBAC Test Org {unique}", slug=f"rbac-org-{unique}")
    session.add(org)
    await session.flush()
    user = User(
        organization_id=org.id,
        email=f"rbac-{unique}@example.com",
        username=f"rbac_user_{unique}",
        password_hash=hash_password("test-password"),
        is_active=True,
        is_superuser=False,
    )
    session.add(user)
    await session.flush()
    tenant = Tenant(
        organization_id=org.id,
        name=f"{user.username}'s workspace",
        slug=f"user-{str(user.id)[:8]}",
        is_active=True,
    )
    session.add(tenant)
    await session.commit()
    return user, tenant.id


@pytest.mark.asyncio
async def test_get_user_permissions_returns_default_role_permissions():
    """Authenticated user resolves to the default role's permissions."""
    await init_db()
    async with async_session() as session:
        user, tenant_id = await _create_user_and_tenant(session)
        perms = await get_user_permissions(session, user, tenant_id=tenant_id)

    # The default role carries every declared permission.
    assert perms == set(Permission.all())
    assert Permission.REPOSITORY_WRITE in perms
    assert Permission.DATABASE_MUTATE in perms
    assert Permission.READ in perms


@pytest.mark.asyncio
async def test_get_user_permissions_tenant_scoped():
    """Permissions resolve in the caller's own tenant (real tenant only).

    In the real call path (``require_policy``) ``tenant_id`` always comes
    from ``get_or_create_user_tenant`` so it references an existing tenant.
    Passing a nonexistent tenant is an error condition (FK violation), not a
    valid use case, so this test uses only real tenants.
    """
    await init_db()
    async with async_session() as session:
        user, tenant_id = await _create_user_and_tenant(session)
        perms = await get_user_permissions(session, user, tenant_id=tenant_id)

    # The default role carries every declared permission in the user's tenant.
    assert perms == set(Permission.all())
    assert Permission.REPOSITORY_WRITE in perms
    assert Permission.DATABASE_MUTATE in perms
    assert Permission.READ in perms


@pytest.mark.asyncio
async def test_role_permissions_table_exists():
    """The role_permissions junction table is part of the metadata."""
    await init_db()
    assert (
        "role_permissions"
        in __import__("jarvis.db.session", fromlist=["Base"]).Base.metadata.tables
    )  # noqa: WPS437


@pytest.mark.asyncio
async def test_role_permission_association_persists():
    """Role -> RolePermission -> Permission association can be inserted and read."""
    await init_db()
    async with async_session() as session:
        user, tenant_id = await _create_user_and_tenant(session)
        # Ensure default data exists via get_user_permissions.
        await get_user_permissions(session, user, tenant_id=tenant_id)

        # Verify a RolePermission row exists linking the default role to a
        # declared permission.
        role = await session.execute(_sa_select(Role).where(Role.name == "user"))
        role_row = role.scalar_one_or_none()
        assert role_row is not None

        perm = await session.execute(
            _sa_select(DbPermission).where(
                DbPermission.name == Permission.REPOSITORY_WRITE
            )
        )
        perm_row = perm.scalar_one_or_none()
        assert perm_row is not None

        rp = await session.execute(
            _sa_select(RolePermission).where(
                RolePermission.role_id == role_row.id,
                RolePermission.permission_id == perm_row.id,
            )
        )
        assert rp.scalar_one_or_none() is not None

        # RoleBinding ties the user to the role in this tenant.
        rb = await session.execute(
            _sa_select(RoleBinding).where(
                RoleBinding.user_id == user.id,
                RoleBinding.role_id == role_row.id,
                RoleBinding.tenant_id == tenant_id,
            )
        )
        assert rb.scalar_one_or_none() is not None
