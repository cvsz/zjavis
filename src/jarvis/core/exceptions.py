"""Custom application exceptions.

All domain exceptions derive from ``JarvisError`` so callers can catch
application-level errors distinctly from unexpected system errors.
"""

from __future__ import annotations


class JarvisError(Exception):
    """Base exception for all JARVIS application errors."""

    def __init__(
        self,
        message: str,
        *,
        code: str | None = None,
        details: dict[str, object] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code or self.__class__.__name__
        self.details = details or {}


class ConfigurationError(JarvisError):
    """Raised when application configuration is invalid or missing."""


class AuthenticationError(JarvisError):
    """Raised when authentication fails."""


class AuthorizationError(JarvisError):
    """Raised when authorization (permission check) fails."""


class NotFoundError(JarvisError):
    """Raised when a requested resource does not exist."""


class ConflictError(JarvisError):
    """Raised when an operation conflicts with current state."""


class ValidationError(JarvisError):
    """Raised when input validation fails."""


class PolicyError(JarvisError):
    """Raised when a policy decision cannot be evaluated or denies an action."""


class ProviderError(JarvisError):
    """Raised when a model provider returns an error."""


class ToolError(JarvisError):
    """Raised when a tool execution fails."""


class TaskError(JarvisError):
    """Raised when a task execution fails."""


class AgentError(JarvisError):
    """Raised when an agent operation fails."""


class MemoryError(JarvisError):
    """Raised when a memory operation fails."""
