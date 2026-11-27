"""Unit tests for the JARVIS smart environment API endpoints."""

from __future__ import annotations

from jarvis.api.smart_environment import DeviceStateRequest


class TestDeviceStateRequest:
    """Tests for DeviceStateRequest model."""

    def test_valid(self) -> None:
        req = DeviceStateRequest(state={"power": "on", "brightness": "80"})
        assert req.state == {"power": "on", "brightness": "80"}

    def test_empty_state(self) -> None:
        req = DeviceStateRequest(state={})
        assert req.state == {}
