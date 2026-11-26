"""Security utilities: password hashing, token creation, secret redaction.

Secrets are never logged or returned in plaintext from these helpers.
"""

from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta
from typing import Any, cast

import bcrypt
from jose import JWTError, jwt  # type: ignore[import-untyped]

from .config import settings
from .exceptions import AuthenticationError, AuthorizationError

# bcrypt has a 72-byte password limit.
_MAX_PASSWORD_BYTES = 72

ALGORITHM = settings.algorithm
APP_SECRET = settings.app_secret
ACCESS_TOKEN_EXPIRE_MINUTES = settings.access_token_expire_minutes


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a bcrypt hash.

    Args:
        plain_password: The plaintext password.
        hashed_password: The stored bcrypt hash.

    Returns:
        True if the password matches, False otherwise.
    """
    try:
        return bcrypt.checkpw(
            plain_password[:_MAX_PASSWORD_BYTES].encode("utf-8"),
            hashed_password.encode("utf-8"),
        )
    except Exception:
        return False


def hash_password(password: str) -> str:
    """Hash a plaintext password using bcrypt.

    Args:
        password: The plaintext password to hash.

    Returns:
        The bcrypt hash string.
    """
    return bcrypt.hashpw(
        password[:_MAX_PASSWORD_BYTES].encode("utf-8"),
        bcrypt.gensalt(),
    ).decode("utf-8")


def create_access_token(
    subject: str,
    *,
    expires_delta: timedelta | None = None,
    additional_claims: dict[str, Any] | None = None,
) -> str:
    """Create a signed JWT access token.

    Args:
        subject: The token subject (typically a user ID).
        expires_delta: Optional custom expiration delta.
        additional_claims: Extra claims to embed in the token.

    Returns:
        The encoded JWT string.
    """
    now = datetime.now(UTC)
    expire = now + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode: dict[str, Any] = {
        "sub": subject,
        "iat": now,
        "exp": expire,
    }
    if additional_claims:
        to_encode.update(additional_claims)
    encoded = cast(str, jwt.encode(to_encode, APP_SECRET, algorithm=ALGORITHM))
    return encoded


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT access token.

    Args:
        token: The JWT string to decode.

    Returns:
        The decoded token payload.

    Raises:
        AuthenticationError: If the token is invalid or expired.
    """
    try:
        payload = cast(dict[str, Any], jwt.decode(token, APP_SECRET, algorithms=[ALGORITHM]))
        return payload
    except JWTError as exc:
        raise AuthenticationError("Invalid or expired token") from exc


def generate_secure_token(length: int = 32) -> str:
    """Generate a cryptographically secure random token.

    Args:
        length: Number of bytes to generate.

    Returns:
        A URL-safe base64-encoded token string.
    """
    return secrets.token_urlsafe(length)


def redact_secret(value: str | None) -> str:
    """Return a redacted representation of a secret value for logging.

    Args:
        value: The secret value, or None.

    Returns:
        "[REDACTED]" if a value is present, otherwise "[NOT_SET]".
    """
    if value is None:
        return "[NOT_SET]"
    if value == "":
        return "[EMPTY]"
    return "[REDACTED]"


class Permission:
    """Capability-style permission identifiers."""

    READ = "system.read"
    REPOSITORY_READ = "repository.read"
    REPOSITORY_WRITE = "repository.write"
    BROWSER_READ = "browser.read"
    BROWSER_INTERACT = "browser.interact"
    TERMINAL_ALLOWLISTED = "terminal.allowlisted"
    CONTAINER_INSPECT = "container.inspect"
    DATABASE_READ = "database.read"
    DATABASE_MUTATE = "database.mutate"
    DEPLOYMENT_REQUEST = "deployment.request"
    DEPLOYMENT_EXECUTE = "deployment.execute"
    SECRETS_METADATA_READ = "secrets.metadata.read"

    @classmethod
    def all(cls) -> list[str]:
        return [
            cls.READ,
            cls.REPOSITORY_READ,
            cls.REPOSITORY_WRITE,
            cls.BROWSER_READ,
            cls.BROWSER_INTERACT,
            cls.TERMINAL_ALLOWLISTED,
            cls.CONTAINER_INSPECT,
            cls.DATABASE_READ,
            cls.DATABASE_MUTATE,
            cls.DEPLOYMENT_REQUEST,
            cls.DEPLOYMENT_EXECUTE,
            cls.SECRETS_METADATA_READ,
        ]


def require_permission(
    user_permissions: set[str],
    required: str,
) -> None:
    """Require that a user holds a specific permission.

    Args:
        user_permissions: The permissions granted to the current user.
        required: The permission required for the action.

    Raises:
        AuthorizationError: If the user does not hold the required permission.
    """
    if required not in user_permissions:
        raise AuthorizationError(
            f"Missing required permission: {required}",
            code="insufficient_permission",
            details={"required": required},
        )
