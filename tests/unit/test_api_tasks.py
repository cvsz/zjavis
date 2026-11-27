"""Unit tests for the JARVIS tasks API endpoints."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from jarvis.api.tasks import TaskCreate, TaskUpdate


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