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
import os
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
    VOICE_READ = "voice.read"
    VOICE_WRITE = "voice.write"
    VISION_READ = "vision.read"

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
            cls.VOICE_READ,
            cls.VOICE_WRITE,
            cls.VISION_READ,
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


# ---------------------------------------------------------------------------
# SSRF Prevention
# ---------------------------------------------------------------------------

# Private/reserved IP ranges per RFC 1918, RFC 5737, RFC 6598, RFC 3927.
# Tool and browser adapters must not resolve or connect to these addresses.
_PRIVATE_IP_NETWORKS: list[tuple[int, int]] = [
    (0x0A000000, 0x0AFFFFFF),  # 10.0.0.0/8
    (0xAC100000, 0xAC1FFFFF),  # 172.16.0.0/12
    (0xC0A80000, 0xC0A8FFFF),  # 192.168.0.0/16
    (0x7F000000, 0x7FFFFFFF),  # 127.0.0.0/8 (loopback)
    (0xA9FE0000, 0xA9FEFFFF),  # 169.254.0.0/16 (link-local)
    (0x00000000, 0x00FFFFFF),  # 0.0.0.0/8 (this network)
    (0xE0000000, 0xEFFFFFFF),  # 224.0.0.0/4 (multicast)
    (0xF0000000, 0xFFFFFFFF),  # 240.0.0.0/4 (reserved)
    (0x64400000, 0x647FFFFF),  # 100.64.0.0/10 (CGN)
]


def _ip_to_int(ip: str) -> int | None:
    """Convert a dotted-quad IPv4 string to an integer, or None."""
    parts = ip.split(".")
    if len(parts) != 4:
        return None
    try:
        vals = [int(p) for p in parts]
    except ValueError:
        return None
    if any(v < 0 or v > 255 for v in vals):
        return None
    return (vals[0] << 24) | (vals[1] << 16) | (vals[2] << 8) | vals[3]


def is_private_ip(host: str) -> bool:
    """Return True if the host resolves to a private/reserved IPv4 address.

    This is a host-name-level heuristic: it checks literal IPv4 addresses
    only. Hostnames that resolve at runtime to private addresses must be
    blocked at the DNS resolution layer by the caller.
    """
    ip = _ip_to_int(host)
    if ip is None:
        return False
    for start, end in _PRIVATE_IP_NETWORKS:
        if start <= ip <= end:
            return True
    return False


def validate_ssrf_safe_url(url: str) -> None:
    """Validate that a URL does not target private or reserved addresses.

    Raises ValidationError if the URL uses an unsafe scheme or targets
    a private/reserved IPv4 address.

    Args:
        url: The URL to validate.

    Raises:
        ValidationError: If the URL is unsafe.
    """
    from jarvis.core.exceptions import ValidationError

    try:
        from urllib.parse import urlparse

        parsed = urlparse(url)
    except Exception as exc:
        raise ValidationError(f"Invalid URL: {url}") from exc

    scheme = parsed.scheme.lower()
    if scheme not in ("http", "https"):
        raise ValidationError(
            f"Unsafe URL scheme: {scheme}. Only http and https are allowed.",
            code="unsafe_url_scheme",
            details={"scheme": scheme, "url": url},
        )

    hostname = parsed.hostname
    if hostname is None:
        raise ValidationError(
            "URL must include a hostname",
            code="missing_hostname",
            details={"url": url},
        )

    if is_private_ip(hostname):
        raise ValidationError(
            f"URL targets private/reserved address: {hostname}",
            code="ssrf_private_address",
            details={"hostname": hostname, "url": url},
        )


# ---------------------------------------------------------------------------
# Path Traversal Prevention
# ---------------------------------------------------------------------------


def validate_safe_path(
    base_dir: str,
    requested_path: str,
    *,
    allow_absolute: bool = False,
) -> str:
    """Validate that a requested path does not escape the base directory.

    Prevents path traversal attacks (e.g. ``../../../etc/passwd``).
    Returns the normalized absolute path if safe.

    Args:
        base_dir: The trusted base directory.
        requested_path: The user-supplied path to validate.
        allow_absolute: Whether absolute paths are permitted.

    Returns:
        The normalized absolute path within base_dir.

    Raises:
        ValidationError: If the path escapes base_dir or is otherwise unsafe.
    """
    from jarvis.core.exceptions import ValidationError

    base = os.path.realpath(base_dir)
    if not os.path.isdir(base):
        raise ValidationError(
            f"Base directory does not exist: {base_dir}",
            code="invalid_base_directory",
            details={"base_dir": base_dir},
        )

    if os.path.isabs(requested_path) and not allow_absolute:
        raise ValidationError(
            "Absolute paths are not allowed",
            code="absolute_path_not_allowed",
            details={"requested_path": requested_path},
        )

    # Reject null bytes and obvious traversal markers
    if "\x00" in requested_path:
        raise ValidationError(
            "Path contains null byte",
            code="path_null_byte",
            details={"requested_path": requested_path},
        )

    combined = os.path.join(base, requested_path)
    normalized = os.path.realpath(combined)

    # Ensure the normalized path is still within base_dir
    if not normalized.startswith(base + os.sep) and normalized != base:
        raise ValidationError(
            "Path traversal detected: path escapes base directory",
            code="path_traversal",
            details={
                "base_dir": base,
                "requested_path": requested_path,
                "resolved": normalized,
            },
        )

    return normalized
