"""Authentication module: user registration, login, password hashing,
token creation, session management, and policy-based authorization.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import Depends, Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from jarvis.core.config import settings  # noqa: F401
from jarvis.core.exceptions import AuthenticationError, AuthorizationError
from jarvis.core.logging import get_logger
from jarvis.core.policy import (
    APPROVAL_REQUIRED_ACTIONS,
    DECISION_ALLOW,
    DECISION_REQUIRE_APPROVAL,
    PolicyDecision,
    PolicyEngine,
)
from jarvis.core.security import (
    Permission,
    create_access_token,
    decode_access_token,
    generate_secure_token,
    hash_password,  # noqa: F401
    redact_secret,  # noqa: F401
    require_permission,  # noqa: F401
    verify_password,
)
from jarvis.db import get_session
from jarvis.db.models import Permission as DbPermission
from jarvis.db.models import Role, RoleBinding, RolePermission, Tenant, User
from jarvis.db.models import Session as DbSession  # noqa: F401

logger = get_logger(__name__)


async def get_or_create_user_tenant(
    session: AsyncSession,
    user: User,
) -> Tenant:
    """Return a tenant for the given user's organization.

    Looks up an existing tenant in the user's organization. If none
    exists, creates a default tenant for that organization so that
    tenant-scoped resources (conversations, tasks, agents, memories)
    can be associated with a valid tenant.

    Args:
        session: Database session.
        user: The authenticated user.

    Returns:
        A Tenant instance associated with the user's organization.
    """
    result = await session.execute(
        select(Tenant).where(Tenant.organization_id == user.organization_id).limit(1)
    )
    tenant = result.scalar_one_or_none()
    if tenant is not None:
        return tenant

    tenant = Tenant(
        organization_id=user.organization_id,
        name=f"{user.username}'s workspace",
        slug=f"user-{str(user.id)[:8]}",
        is_active=True,
    )
    session.add(tenant)
    await session.commit()
    await session.refresh(tenant)
    logger.info(
        "Created default tenant for user",
        extra={"user_id": str(user.id), "tenant_id": str(tenant.id)},
    )
    return tenant


async def authenticate_user(
    session: AsyncSession, username: str, password: str
) -> User:
    """Authenticate a user by username and password.

    Args:
        session: Database session.
        username: The username to authenticate.
        password: The plaintext password.

    Returns:
        The authenticated User.

    Raises:
        AuthenticationError: If credentials are invalid.
    """
    result = await session.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if user is None:
        logger.warning(
            "Authentication failed: user not found", extra={"username": username}
        )
        raise AuthenticationError("Invalid username or password")
    if not verify_password(password, user.password_hash):
        logger.warning(
            "Authentication failed: invalid password", extra={"username": username}
        )
        raise AuthenticationError("Invalid username or password")
    if not user.is_active:
        raise AuthenticationError("User account is disabled")
    return user


def create_tokens_for_user(user: User) -> dict[str, str]:
    """Create access and refresh tokens for an authenticated user.

    Args:
        user: The authenticated user.

    Returns:
        A dict with ``access_token`` and ``refresh_token``.
    """
    jwt_token = create_access_token(
        str(user.id),
        additional_claims={
            "username": user.username,
            "is_superuser": user.is_superuser,
        },
    )
    refresh_token = generate_secure_token()
    return {
        "access_token": jwt_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


async def get_current_user(
    session: AsyncSession,
    authorization: str | None,
) -> User:
    """Extract and validate the current user from a Bearer token.

    Args:
        session: Database session.
        authorization: The Authorization header value (e.g. ``Bearer <token>``).

    Returns:
        The authenticated User.

    Raises:
        AuthenticationError: If the token is missing, malformed, or invalid.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise AuthenticationError("Missing or invalid authorization header")
    token = authorization.split(" ", 1)[1]
    payload = decode_access_token(token)
    user_id_str = payload.get("sub")
    if not user_id_str:
        raise AuthenticationError("Token missing subject")
    try:
        user_id = UUID(user_id_str)
    except ValueError:
        raise AuthenticationError("Invalid token subject")
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise AuthenticationError("User not found")
    if not user.is_active:
        raise AuthenticationError("User account is disabled")
    return user


def require_superuser(user: User) -> None:
    """Require that the current user is a superuser.

    Args:
        user: The current user.

    Raises:
        AuthorizationError: If the user is not a superuser.
    """
    if not user.is_superuser:
        raise AuthorizationError(
            "Superuser access required",
            code="insufficient_privilege",
            details={"required": "is_superuser"},
        )


async def get_user_permissions(
    session: AsyncSession,
    user: User,
    tenant_id: UUID | None = None,
) -> set[str]:
    """Resolve the set of permission names granted to a user through role bindings.

    Queries role_bindings -> role_permissions -> permissions to collect every
    atomic permission name the user holds within their tenant scope. When
    ``tenant_id`` is provided, only permissions scoped to that tenant are
    returned, enforcing tenant isolation at the authorization layer.

    The default role ("user", carrying every ``Permission.all()`` permission)
    and the caller's role binding are self-provisioned idempotently so that
    authenticated users can pass execution-time policy checks out of the box.
    High-risk actions (``database.mutate``, ``deployment.execute``) still
    require explicit approval via the PolicyEngine's
    ``APPROVAL_REQUIRED_ACTIONS``.

    Args:
        session: Database session.
        user: The authenticated user.
        tenant_id: Optional tenant ID to scope permissions to.

    Returns:
        A set of permission name strings (e.g. ``{"repository.read", "database.read"}``).
    """
    # Resolve tenant when not explicitly provided.
    if tenant_id is None:
        tenant = await get_or_create_user_tenant(session, user)
        tenant_id = tenant.id

    # Self-provision default permissions, role, and role binding (idempotent).
    await _ensure_default_permissions_and_role(session, user, tenant_id)

    query = (
        select(DbPermission.name)
        .join(RolePermission, RolePermission.permission_id == DbPermission.id)
        .join(RoleBinding, RoleBinding.role_id == RolePermission.role_id)
        .where(RoleBinding.user_id == user.id)
    )
    if tenant_id is not None:
        query = query.where(RoleBinding.tenant_id == tenant_id)
    result = await session.execute(query)
    return {row[0] for row in result.all()}


async def _ensure_default_permissions_and_role(
    session: AsyncSession,
    user: User,
    tenant_id: UUID | None = None,
) -> None:
    """Idempotently seed default permissions, a default role, and the caller's
    role binding so permission resolution is self-configuring.

    Grants the authenticated user the default role within their tenant. The
    default role carries every declared permission; execution-time policy
    decisions (including the approval gate for ``database.mutate`` and
    ``deployment.execute``) still enforce least privilege at the action level.
    Writes are flushed but not committed so the request's owning handler
    retains transaction control; the seeding re-establishes itself each
    request, which is safe and idempotent.
    """
    from sqlalchemy import select as _sa_select

    if tenant_id is None:
        tenant = await get_or_create_user_tenant(session, user)
        tenant_id = tenant.id

    # 1. Seed every declared permission (idempotent by unique name).
    for perm_name in Permission.all():
        existing = await session.execute(
            _sa_select(DbPermission).where(DbPermission.name == perm_name)
        )
        if existing.scalar_one_or_none() is None:
            session.add(DbPermission(name=perm_name))
    await session.flush()

    # 2. Ensure the default role exists.
    result = await session.execute(_sa_select(Role).where(Role.name == "user"))
    role = result.scalar_one_or_none()
    if role is None:
        role = Role(
            name="user",
            description="Default role for authenticated users",
        )
        session.add(role)
        await session.flush()

    # 3. Grant all permissions to the default role (idempotent).
    perms = await session.execute(_sa_select(DbPermission))
    for perm in perms.scalars().all():
        rp = await session.execute(
            _sa_select(RolePermission).where(
                RolePermission.role_id == role.id,
                RolePermission.permission_id == perm.id,
            )
        )
        if rp.scalar_one_or_none() is None:
            session.add(RolePermission(role_id=role.id, permission_id=perm.id))
    await session.flush()

    # 4. Bind the caller to the default role in their tenant (idempotent).
    rb = await session.execute(
        _sa_select(RoleBinding).where(
            RoleBinding.user_id == user.id,
            RoleBinding.role_id == role.id,
            RoleBinding.tenant_id == tenant_id,
        )
    )
    if rb.scalar_one_or_none() is None:
        session.add(RoleBinding(user_id=user.id, role_id=role.id, tenant_id=tenant_id))
    await session.flush()


def require_policy(
    required_permission: str | None = None,
    action: str = "",
    risk_level: str = "low",
    require_approval_on: frozenset[str] | None = None,
) -> Any:
    """Return a FastAPI dependency that authenticates and enforces policy.

    Combines authentication (Bearer token) with a PolicyEngine decision
    evaluated at request time. Raises :class:`AuthorizationError` when the
    decision is DENY, OUT_OF_SCOPE, or REQUIRE_APPROVAL without an explicit
    grant.

    Args:
        required_permission: Permission name required for the action.
        action: Human-readable description of the action (for audit logging).
        risk_level: Risk classification (low, medium, high, critical).
        require_approval_on: Additional permission names that always require
            approval beyond the built-in approval-required set.

    Returns:
        A FastAPI :class:`Depends` that resolves to the authenticated and
        authorized :class:`User`.

    Raises:
        AuthenticationError: If the token is missing or invalid.
        AuthorizationError: If policy denies the action or approval is required.
    """

    async def _dependency(
        session: AsyncSession = Depends(get_session),  # noqa: B008
        authorization: str | None = Header(default=None, alias="Authorization"),
    ) -> User:
        user = await get_current_user(session, authorization)

        # If no specific permission is required, authentication alone is
        # sufficient for read-safe actions.
        if required_permission is None:
            return user

        # Resolve tenant for isolation-scoped permissions.
        tenant = await get_or_create_user_tenant(session, user)
        user_permissions = await get_user_permissions(
            session, user, tenant_id=tenant.id
        )

        engine = PolicyEngine()

        # Combine built-in approval-required actions with caller-specified ones.
        approval_required = set(APPROVAL_REQUIRED_ACTIONS)
        if require_approval_on:
            approval_required |= set(require_approval_on)

        decision = engine.evaluate(
            actor_permissions=user_permissions,
            required_permission=required_permission,
            action=action or f"{required_permission}:{action}",
            actor_id=str(user.id),
            tenant_id=str(tenant.id),
            risk_level=risk_level,
        )

        # Override to REQUIRE_APPROVAL when the permission is in the
        # approval-required set, even if the policy engine returned ALLOW.
        if (
            decision.decision == DECISION_ALLOW
            and required_permission in approval_required
        ):
            decision = PolicyDecision(
                decision=DECISION_REQUIRE_APPROVAL,
                reason=f"Action requires explicit approval: {action}",
                required_permission=required_permission,
                requires_approval=True,
            )

        if decision.decision == DECISION_REQUIRE_APPROVAL:
            raise AuthorizationError(
                decision.reason,
                code="approval_required",
                details={
                    "required_permission": decision.required_permission,
                    "requires_approval": True,
                },
            )

        if decision.denied:
            raise AuthorizationError(
                decision.reason,
                code="insufficient_permission",
                details={
                    "required_permission": decision.required_permission,
                    "user_permissions": sorted(user_permissions),
                },
            )

        return user

    return _dependency
