"""Security utilities: password hashing, token creation, secret redaction.

Secrets are never logged or returned in plaintext from these helpers.
Tokens use HMAC-SHA256 signing from the Python standard library,
avoiding third-party JWT libraries with known vulnerabilities.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any, cast

from .config import settings
from .exceptions import AuthenticationError, AuthorizationError

# PBKDF2 iterations for password hashing (OWASP recommended minimum: 210,000 as of 2023)
_PBKDF2_ITERATIONS = 210000

APP_SECRET = settings.app_secret
ACCESS_TOKEN_EXPIRE_MINUTES = settings.access_token_expire_minutes


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a PBKDF2-HMAC-SHA256 hash.

    Args:
        plain_password: The plaintext password.
        hashed_password: The stored hash in ``$pbkdf2-sha256$iterations$salt$hash`` format.

    Returns:
        True if the password matches, False otherwise.
    """
    try:
        parts = hashed_password.split("$")
        if len(parts) != 5 or parts[0] != "" or parts[1] != "pbkdf2-sha256":
            return False
        _, _, iterations_str, salt_b64, hash_b64 = parts
        iterations = int(iterations_str)
        salt = base64.b64decode(salt_b64)
        expected_hash = base64.b64decode(hash_b64)
        computed_hash = hashlib.pbkdf2_hmac(
            "sha256",
            plain_password.encode("utf-8"),
            salt,
            iterations,
        )
        return hmac.compare_digest(expected_hash, computed_hash)
    except Exception:  # noqa: BLE001 — return False on any verification error
        return False


def hash_password(password: str) -> str:
    """Hash a plaintext password using PBKDF2-HMAC-SHA256.

    Args:
        password: The plaintext password to hash.

    Returns:
        The hash string in ``$pbkdf2-sha256$iterations$salt$hash`` format.
    """
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        _PBKDF2_ITERATIONS,
    )
    return (
        f"$pbkdf2-sha256${_PBKDF2_ITERATIONS}$"
        f"{base64.b64encode(salt).decode('ascii')}$"
        f"{base64.b64encode(dk).decode('ascii')}"
    )


def _encode_b64j(json_obj: dict[str, Any]) -> str:
    """Base64url-encode a JSON object without padding."""
    json_bytes = json.dumps(json_obj, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(json_bytes).rstrip(b"=").decode("ascii")


def _decode_b64j(b64str: str) -> dict[str, Any]:
    """Decode a base64url-encoded JSON object."""
    padding = "=" * (4 - len(b64str) % 4)
    json_bytes = base64.urlsafe_b64decode(b64str + padding)
    return cast(dict[str, Any], json.loads(json_bytes))


def _sign(payload: str, secret: str) -> str:
    """Create an HMAC-SHA256 signature for the payload."""
    return hmac.new(
        secret.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256
    ).hexdigest()


def _verify_signature(payload: str, signature: str, secret: str) -> bool:
    """Verify an HMAC-SHA256 signature using constant-time comparison."""
    expected = _sign(payload, secret)
    return hmac.compare_digest(signature, expected)


def create_access_token(
    subject: str,
    *,
    expires_delta: timedelta | None = None,
    additional_claims: dict[str, Any] | None = None,
) -> str:
    """Create a signed access token.

    Uses HMAC-SHA256 signing from the standard library. Tokens are
    self-contained: header, payload, and signature are all included.

    Args:
        subject: The token subject (typically a user ID).
        expires_delta: Optional custom expiration delta.
        additional_claims: Extra claims to embed in the token.

    Returns:
        The encoded token string in ``header.payload.signature`` format.
    """
    now = datetime.now(UTC)
    expire = now + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))

    header = {"alg": "HS256", "typ": "JWT"}
    payload: dict[str, Any] = {
        "sub": subject,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }
    if additional_claims:
        payload.update(additional_claims)

    header_b64 = _encode_b64j(header)
    payload_b64 = _encode_b64j(payload)
    signing_input = f"{header_b64}.{payload_b64}"
    signature = _sign(signing_input, APP_SECRET)

    return f"{signing_input}.{signature}"


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode and validate an access token.

    Args:
        token: The token string in ``header.payload.signature`` format.

    Returns:
        The decoded token payload.

    Raises:
        AuthenticationError: If the token is invalid, expired, or
            the signature does not match.
    """
    try:
        parts = token.split(".")
        if len(parts) != 3:
            raise ValueError("Token must have three parts")
        header_b64, payload_b64, signature = parts

        # Verify signature first (before decoding payload to avoid
        # processing untrusted data)
        signing_input = f"{header_b64}.{payload_b64}"
        if not _verify_signature(signing_input, signature, APP_SECRET):
            raise ValueError("Invalid signature")

        payload = _decode_b64j(payload_b64)

        # Check expiration
        exp = payload.get("exp")
        if exp is not None:
            now_ts = int(datetime.now(UTC).timestamp())
            if now_ts >= exp:
                raise ValueError("Token has expired")

        return payload
    except (ValueError, KeyError, json.JSONDecodeError) as exc:
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
