"""Smart environment: IoT device provider abstraction.

Per JARVIS blueprint, smart environment capabilities are gated behind the
``smart_environment_enabled`` configuration flag. Providers follow the same
adapter pattern as the model gateway. No device credentials are embedded;
configuration comes from environment variables.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from jarvis.core.config import settings


class SmartEnvironmentProvider(ABC):
    """Abstract base class for smart environment / IoT providers."""

    @abstractmethod
    async def list_devices(self) -> list[dict[str, Any]]:
        """List all available devices.

        Returns:
            List of device dicts with at least ``id`` and ``name`` keys.
        """

    @abstractmethod
    async def get_device_state(self, device_id: str) -> dict[str, Any]:
        """Get the current state of a device.

        Args:
            device_id: The device identifier.

        Returns:
            Dict with device state information.
        """

    @abstractmethod
    async def set_device_state(
        self, device_id: str, state: dict[str, Any]
    ) -> dict[str, Any]:
        """Set the state of a device.

        Args:
            device_id: The device identifier.
            state: Desired state key-value pairs.

        Returns:
            Dict with the resulting device state.
        """


class LocalSmartEnvironmentProvider(SmartEnvironmentProvider):
    """Local smart environment provider — placeholder implementation.

    Returns empty results, keeping the system functional without
    IoT hardware while the ``smart_environment_enabled`` flag is false.
    """

    async def list_devices(self) -> list[dict[str, Any]]:
        return []

    async def get_device_state(self, device_id: str) -> dict[str, Any]:
        return {
            "device_id": device_id,
            "state": "unknown",
            "provider": "local",
            "error": "local smart environment not implemented",
        }

    async def set_device_state(
        self, device_id: str, state: dict[str, Any]
    ) -> dict[str, Any]:
        return {
            "device_id": device_id,
            "state": state,
            "provider": "local",
            "error": "local smart environment not implemented",
        }


class SmartEnvironmentService:
    """High-level smart environment service that delegates to a provider.

    Raises :class:`RuntimeError` if smart environment is not enabled in
    configuration.
    """

    def __init__(
        self,
        *,
        provider: SmartEnvironmentProvider | None = None,
        enabled: bool = False,
    ) -> None:
        self.provider = provider or LocalSmartEnvironmentProvider()
        self.enabled = enabled

    def _require_enabled(self) -> None:
        if not self.enabled:
            raise RuntimeError(
                "Smart environment is disabled. "
                "Set JARVIS_SMART_ENVIRONMENT_ENABLED=true to enable."
            )

    async def list_devices(self) -> list[dict[str, Any]]:
        self._require_enabled()
        return await self.provider.list_devices()

    async def get_device_state(self, device_id: str) -> dict[str, Any]:
        self._require_enabled()
        return await self.provider.get_device_state(device_id)

    async def set_device_state(
        self, device_id: str, state: dict[str, Any]
    ) -> dict[str, Any]:
        self._require_enabled()
        return await self.provider.set_device_state(device_id, state)


smart_environment = SmartEnvironmentService(
    provider=LocalSmartEnvironmentProvider(),
    enabled=settings.smart_environment_enabled,
)
