"""Unit tests for the JARVIS tasks API endpoints."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from jarvis.api.main import _permission_for_path, _risk_level_for_path
from jarvis.api.tasks import TaskCreate, TaskUpdate
from jarvis.core.security import Permission


class TestTaskCreate:
    """Tests for TaskCreate model."""

    def test_task_create_valid(self) -> None:
        req = TaskCreate(task_type="process_data", risk_classification="low")
        assert req.task_type == "process_data"
        assert req.risk_classification == "low"
        assert req.agent_id is None
        assert req.idempotency_key is None

    def test_task_create_with_agent(self) -> None:
        import uuid

        agent_id = uuid.uuid4()
        req = TaskCreate(
            task_type="analyze",
            risk_classification="high",
            agent_id=agent_id,
            idempotency_key="key-123",
        )
        assert req.agent_id == agent_id
        assert req.idempotency_key == "key-123"

    def test_task_create_defaults(self) -> None:
        req = TaskCreate(task_type="test")
        assert req.risk_classification == "low"
        assert req.idempotency_key is None

    def test_task_create_task_type_empty(self) -> None:
        with pytest.raises(ValidationError):
            TaskCreate(task_type="")

    def test_task_create_task_type_too_long(self) -> None:
        with pytest.raises(ValidationError):
            TaskCreate(task_type="x" * 101)

    def test_task_create_risk_too_long(self) -> None:
        with pytest.raises(ValidationError):
            TaskCreate(task_type="test", risk_classification="x" * 51)


class TestTaskUpdate:
    """Tests for TaskUpdate model."""

    def test_task_update_valid(self) -> None:
        req = TaskUpdate(state="completed")
        assert req.state == "completed"

    def test_task_update_all_fields(self) -> None:
        import uuid

        agent_id = uuid.uuid4()
        req = TaskUpdate(
            task_type="new_type",
            risk_classification="medium",
            agent_id=agent_id,
            state="running",
            idempotency_key="new-key",
        )
        assert req.task_type == "new_type"
        assert req.risk_classification == "medium"
        assert req.agent_id == agent_id
        assert req.state == "running"
        assert req.idempotency_key == "new-key"

    def test_task_update_empty(self) -> None:
        req = TaskUpdate()
        assert req.task_type is None
        assert req.state is None


class TestPermissionPathMapping:
    """Tests for _permission_for_path — maps API paths to required permissions."""

    def test_conversation_post_requires_write(self) -> None:
        assert (
            _permission_for_path("/api/v1/conversations", "POST")
            == Permission.REPOSITORY_WRITE
        )

    def test_conversation_get_requires_read(self) -> None:
        assert (
            _permission_for_path("/api/v1/conversations", "GET")
            == Permission.REPOSITORY_READ
        )

    def test_memory_post_requires_write(self) -> None:
        assert (
            _permission_for_path("/api/v1/memory", "POST")
            == Permission.REPOSITORY_WRITE
        )

    def test_memory_delete_requires_write(self) -> None:
        assert (
            _permission_for_path("/api/v1/memory", "DELETE")
            == Permission.REPOSITORY_WRITE
        )

    def test_task_post_requires_write(self) -> None:
        assert _permission_for_path("/api/v1/tasks", "POST") == Permission.REPOSITORY_WRITE

    def test_task_get_requires_read(self) -> None:
        assert _permission_for_path("/api/v1/tasks", "GET") == Permission.REPOSITORY_READ

    def test_agent_runtime_requires_write(self) -> None:
        assert (
            _permission_for_path("/api/v1/agent-runtime/execute", "POST")
            == Permission.REPOSITORY_WRITE
        )

    def test_audit_requires_read(self) -> None:
        assert _permission_for_path("/api/v1/audit/events", "GET") == Permission.REPOSITORY_READ

    def test_unknown_path_defaults_read(self) -> None:
        assert _permission_for_path("/api/v1/unknown", "GET") == Permission.REPOSITORY_READ


class TestRiskLevelClassification:
    """Tests for _risk_level_for_path — classifies path risk levels."""

    def test_tasks_is_medium_risk(self) -> None:
        assert _risk_level_for_path("/api/v1/tasks") == "medium"

    def test_agent_runtime_is_medium_risk(self) -> None:
        assert _risk_level_for_path("/api/v1/agent-runtime/execute") == "medium"

    def test_smart_environment_is_medium_risk(self) -> None:
        assert _risk_level_for_path("/api/v1/smart-environment/devices") == "medium"

    def test_conversation_is_low_risk(self) -> None:
        assert _risk_level_for_path("/api/v1/conversations") == "low"

    def test_unknown_path_is_low_risk(self) -> None:
        assert _risk_level_for_path("/api/v1/unknown") == "low"
