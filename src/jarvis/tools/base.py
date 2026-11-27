"""Base classes for capability tool adapters.

All capability adapters inherit from ``BaseToolAdapter`` and implement
typed, validated, audited access to external systems. Adapters are
disabled by default and must be explicitly enabled via configuration.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class ToolResult:
    """Standardized result from a tool adapter execution.

    Attributes:
        success: Whether the operation completed successfully.
        data: Operation result data (implementation-defined).
        error: Error message if the operation failed.
        provider: Identifier of the underlying provider/adapter.
        metadata: Additional structured metadata (no secrets).
    """

    def __init__(
        self,
        *,
        success: bool,
        data: Any = None,
        error: str | None = None,
        provider: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.success = success
        self.data = data
        self.error = error
        self.provider = provider
        self.metadata = metadata or {}

    def to_dict(self) -> dict[str, Any]:
        """Serialize the result to a dict suitable for JSON responses."""
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "provider": self.provider,
            "metadata": self.metadata,
        }


class BaseToolAdapter(ABC):
    """Abstract base class for all capability tool adapters.

    Concrete adapters must implement the operation-specific methods
    declared by their subclass interface. All adapters enforce:
    - No embedded credentials (configuration-driven only)
    - Input validation before execution
    - Timeout-bounded execution
    - No secret leakage in results or logs
    """

    def __init__(self, *, provider_name: str, enabled: bool = False) -> None:
        self.provider_name = provider_name
        self.enabled = enabled

    def _require_enabled(self) -> None:
        """Raise if the adapter is not enabled in configuration."""
        if not self.enabled:
            raise RuntimeError(
                f"{self.provider_name} tool adapter is disabled. "
                f"Enable via configuration to use this capability."
            )

    @abstractmethod
    async def execute(self, *, action: str, params: dict[str, Any]) -> ToolResult:
        """Execute a tool action with validated parameters.

        Args:
            action: The specific operation to perform.
            params: Validated input parameters for the action.

        Returns:
            A :class:`ToolResult` with the operation outcome.
        """
        raise NotImplementedError

    @property
    def api_name(self) -> str:
        """Return the adapter's public API name."""
        return self.provider_name


__all__ = [
    "BaseToolAdapter",
    "ToolResult",
]
