"""Authentication module: user registration, login, password hashing,
token creation, and session management.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from jarvis.core.config import settings  # noqa: F401
from jarvis.core.exceptions import AuthenticationError, AuthorizationError
from jarvis.core.logging import get_logger
from jarvis.core.security import (
    create_access_token,
    decode_access_token,
    generate_secure_token,
    hash_password,  # noqa: F401
    redact_secret,  # noqa: F401
    require_permission,  # noqa: F401
    verify_password,
)
from jarvis.db.models import Session as DbSession  # noqa: F401
from jarvis.db.models import User

logger = get_logger(__name__)


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
        logger.warning("Authentication failed: user not found", extra={"username": username})
        raise AuthenticationError("Invalid username or password")
    if not verify_password(password, user.password_hash):  # type: ignore[arg-type]
        logger.warning("Authentication failed: invalid password", extra={"username": username})
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
        additional_claims={"username": user.username, "is_superuser": user.is_superuser},
    )
    refresh_token = generate_secure_token()
    return {"access_token": jwt_token, "refresh_token": refresh_token, "token_type": "bearer"}


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
