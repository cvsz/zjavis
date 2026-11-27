"""Unit tests for the JARVIS agents API endpoints."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from jarvis.api.agents import AgentCreate, AgentUpdate


class TestAgentCreate:
    """Tests for AgentCreate model."""

    def test_agent_create_valid(self) -> None:
        req = AgentCreate(name="Test Agent", version="1.0.0")
        assert req.name == "Test Agent"
        assert req.version == "1.0.0"
        assert req.description is None
        assert req.max_runtime_seconds == 300
        assert req.max_tool_calls == 50

    def test_agent_create_all_fields(self) -> None:
        req = AgentCreate(
            name="Analyzer",
            version="2.0.0",
            description="Analyzes data",
            max_runtime_seconds=600,
            max_tool_calls=100,
        )
        assert req.name == "Analyzer"
        assert req.version == "2.0.0"
        assert req.description == "Analyzes data"
        assert req.max_runtime_seconds == 600
        assert req.max_tool_calls == 100

    def test_agent_create_name_empty(self) -> None:
        with pytest.raises(ValidationError):
            AgentCreate(name="")

    def test_agent_create_name_too_long(self) -> None:
        with pytest.raises(ValidationError):
            AgentCreate(name="x" * 256)

    def test_agent_create_max_runtime_zero(self) -> None:
        with pytest.raises(ValidationError):
            AgentCreate(name="test", max_runtime_seconds=0)

    def test_agent_create_max_tool_calls_zero(self) -> None:
        with pytest.raises(ValidationError):
            AgentCreate(name="test", max_tool_calls=0)


class TestAgentUpdate:
    """Tests for AgentUpdate model."""

    def test_agent_update_partial(self) -> None:
        req = AgentUpdate(is_active=False)
        assert req.is_active is False
        assert req.name is None

    def test_agent_update_all_fields(self) -> None:
        req = AgentUpdate(
            name="Updated",
            version="3.0.0",
            description="New desc",
            is_active=True,
            max_runtime_seconds=120,
            max_tool_calls=25,
        )
        assert req.name == "Updated"
        assert req.version == "3.0.0"
        assert req.description == "New desc"
        assert req.is_active is True
        assert req.max_runtime_seconds == 120
        assert req.max_tool_calls == 25

    def test_agent_update_max_runtime_zero(self) -> None:
        with pytest.raises(ValidationError):
            AgentUpdate(max_runtime_seconds=0)
