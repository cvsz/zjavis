"""Unit tests for the JARVIS Smart Environment service stub (Phase 9 — BLOCKED without IoT hardware/credentials)."""

from __future__ import annotations

import asyncio

import pytest

from jarvis.ai.smart_environment import (
    LocalSmartEnvironmentProvider,
    SmartEnvironmentService,
)


class TestLocalSmartEnvironmentProvider:
    """Tests for the local (stub) smart environment provider."""

    def test_list_devices_returns_empty(self) -> None:
        provider = LocalSmartEnvironmentProvider()
        result = asyncio.run(provider.list_devices())
        assert result == []

    def test_get_device_state_returns_stub(self) -> None:
        provider = LocalSmartEnvironmentProvider()
        result = asyncio.run(provider.get_device_state("d1"))
        assert result["device_id"] == "d1"
        assert result["state"] == "unknown"
        assert result["provider"] == "local"
        assert result["error"] == "local smart environment not implemented"

    def test_set_device_state_returns_stub(self) -> None:
        provider = LocalSmartEnvironmentProvider()
        result = asyncio.run(
            provider.set_device_state("d1", {"power": "on", "brightness": "80"})
        )
        assert result["device_id"] == "d1"
        assert result["state"] == {"power": "on", "brightness": "80"}
        assert result["provider"] == "local"
        assert result["error"] == "local smart environment not implemented"


class TestSmartEnvironmentServiceDisabled:
    """SmartEnvironmentService raises RuntimeError when disabled (secure-by-default)."""

    def test_list_devices_when_disabled(self) -> None:
        service = SmartEnvironmentService(
            provider=LocalSmartEnvironmentProvider(), enabled=False
        )
        with pytest.raises(RuntimeError, match="Smart environment is disabled"):
            asyncio.run(service.list_devices())

    def test_get_device_state_when_disabled(self) -> None:
        service = SmartEnvironmentService(
            provider=LocalSmartEnvironmentProvider(), enabled=False
        )
        with pytest.raises(RuntimeError, match="Smart environment is disabled"):
            asyncio.run(service.get_device_state("d1"))

    def test_set_device_state_when_disabled(self) -> None:
        service = SmartEnvironmentService(
            provider=LocalSmartEnvironmentProvider(), enabled=False
        )
        with pytest.raises(RuntimeError, match="Smart environment is disabled"):
            asyncio.run(service.set_device_state("d1", {"power": "on"}))


class TestSmartEnvironmentServiceEnabled:
    """SmartEnvironmentService delegates to provider when enabled."""

    def test_list_devices_delegates(self) -> None:
        service = SmartEnvironmentService(
            provider=LocalSmartEnvironmentProvider(), enabled=True
        )
        result = asyncio.run(service.list_devices())
        assert result == []

    def test_get_device_state_delegates(self) -> None:
        service = SmartEnvironmentService(
            provider=LocalSmartEnvironmentProvider(), enabled=True
        )
        result = asyncio.run(service.get_device_state("d1"))
        assert result["error"] == "local smart environment not implemented"

    def test_set_device_state_delegates(self) -> None:
        service = SmartEnvironmentService(
            provider=LocalSmartEnvironmentProvider(), enabled=True
        )
        result = asyncio.run(service.set_device_state("d1", {"power": "on"}))
        assert result["error"] == "local smart environment not implemented"

    def test_default_provider_is_local(self) -> None:
        service = SmartEnvironmentService(enabled=True)
        assert isinstance(service.provider, LocalSmartEnvironmentProvider)
