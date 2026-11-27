"""Unit tests for the JARVIS orchestration engine."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from jarvis.core.exceptions import TaskError
from jarvis.db.models import Task
from jarvis.orchestration import (
    DEFAULT_MAX_RETRIES,
    MAX_DELEGATION_DEPTH,
    VALID_STATES,
    OrchestrationEngine,
    TaskContext,
)


class _FakeSession:
    """In-memory fake session mimicking AsyncSession behavior for tests."""

    def __init__(self) -> None:
        self._tasks: dict[Any, Task] = {}
        self.committed = False

    def add(self, task: Task) -> None:
        self._tasks[task.id] = task

    async def execute(self, stmt: Any) -> MagicMock:
        if hasattr(stmt, "_where_criteria"):
            for criterion in stmt._where_criteria:  # type: ignore[attr-defined]
                if hasattr(criterion, "right") and hasattr(criterion.right, "value"):
                    task_id = criterion.right.value
                    task = self._tasks.get(task_id)
                    mock = MagicMock()
                    mock.scalar_one_or_none.return_value = task
                    return mock
        mock = MagicMock()
        mock.scalar_one_or_none.return_value = None
        return mock

    async def commit(self) -> None:
        self.committed = True

    async def refresh(self, obj: Any) -> None:
        pass


def _make_task(
    session: _FakeSession,
    task_id: Any = None,
    state: str = "queued",
    retry_count: int = 0,
    tenant_id: Any = None,
    user_id: Any = None,
    task_type: str = "test",
    risk_classification: str = "low",
    max_runtime_seconds: int = 300,
    max_tool_calls: int = 50,
    idempotency_key: str | None = None,
    started_at: Any = None,
    completed_at: Any = None,
    error_message: str | None = None,
) -> Task:
    task = Task(
        id=task_id or uuid4(),
        tenant_id=tenant_id or uuid4(),
        user_id=user_id or uuid4(),
        task_type=task_type,
        risk_classification=risk_classification,
        state=state,
        idempotency_key=idempotency_key,
        retry_count=retry_count,
        started_at=started_at,
        completed_at=completed_at,
        error_message=error_message,
    )
    session.add(task)
    return task


class TestTaskContext:
    """Tests for TaskContext bounds checking."""

    def test_is_expired_future(self) -> None:
        ctx = TaskContext(
            task_id=uuid4(),
            tenant_id=None,
            user_id=None,
            task_type="t",
            risk_classification="low",
            max_runtime_seconds=300,
            max_tool_calls=50,
        )
        ctx.deadline = datetime.now(UTC) + timedelta(seconds=60)
        assert ctx.is_expired is False
        assert ctx.remaining_seconds is not None
        assert ctx.remaining_seconds > 0

    def test_is_expired_past(self) -> None:
        ctx = TaskContext(
            task_id=uuid4(),
            tenant_id=None,
            user_id=None,
            task_type="t",
            risk_classification="low",
            max_runtime_seconds=300,
            max_tool_calls=50,
        )
        ctx.deadline = datetime.now(UTC) - timedelta(seconds=1)
        assert ctx.is_expired is True
        assert ctx.remaining_seconds == 0.0

    def test_mark_cancelled(self) -> None:
        ctx = TaskContext(
            task_id=uuid4(),
            tenant_id=None,
            user_id=None,
            task_type="t",
            risk_classification="low",
            max_runtime_seconds=300,
            max_tool_calls=50,
        )
        assert ctx.is_cancelled is False
        ctx.mark_cancelled()
        assert ctx.is_cancelled is True

    def test_check_bounds_cancelled(self) -> None:
        ctx = TaskContext(
            task_id=uuid4(),
            tenant_id=None,
            user_id=None,
            task_type="t",
            risk_classification="low",
            max_runtime_seconds=300,
            max_tool_calls=50,
        )
        ctx.mark_cancelled()
        with pytest.raises(TaskError) as exc:
            ctx.check_bounds()
        assert exc.value.code == "task_cancelled"

    def test_check_bounds_expired(self) -> None:
        ctx = TaskContext(
            task_id=uuid4(),
            tenant_id=None,
            user_id=None,
            task_type="t",
            risk_classification="low",
            max_runtime_seconds=300,
            max_tool_calls=50,
        )
        ctx.deadline = datetime.now(UTC) - timedelta(seconds=1)
        with pytest.raises(TaskError) as exc:
            ctx.check_bounds()
        assert exc.value.code == "task_deadline_exceeded"


class TestOrchestrationEngine:
    """Tests for OrchestrationEngine."""

    @pytest.fixture
    def session(self) -> _FakeSession:
        return _FakeSession()

    @pytest.fixture
    def engine(self, session: _FakeSession) -> OrchestrationEngine:
        return OrchestrationEngine(session=session)

    @pytest.mark.asyncio
    async def test_execute_success(
        self, engine: OrchestrationEngine, session: _FakeSession
    ) -> None:
        task = _make_task(session, state="queued")

        async def handler(ctx: TaskContext) -> str:
            assert ctx.state == "running"
            return "done"

        result = await engine.execute(task_id=task.id, handler=handler)
        assert result["state"] == "completed"
        assert result["response"] == "done"

    @pytest.mark.asyncio
    async def test_execute_cancelled(
        self, engine: OrchestrationEngine, session: _FakeSession
    ) -> None:
        task = _make_task(session, state="queued")

        async def handler(ctx: TaskContext) -> str:
            if ctx.is_cancelled:
                raise TaskError("cancelled", code="task_cancelled")
            return "done"

        # Cancel via the active context path: call cancel first, which
        # persists cancellation to the database
        await engine.cancel(task.id)
        result = await engine.execute(task_id=task.id, handler=handler)
        assert result["state"] == "cancelled"
        assert result.get("cancelled") is True

    @pytest.mark.asyncio
    async def test_execute_retry_then_success(
        self, engine: OrchestrationEngine, session: _FakeSession
    ) -> None:
        task = _make_task(session, state="queued")
        attempts = 0

        async def handler(ctx: TaskContext) -> str:
            nonlocal attempts
            attempts += 1
            if attempts < 2:
                raise ValueError("transient")
            return "done"

        result = await engine.execute(task_id=task.id, handler=handler)
        assert result["state"] == "completed"
        assert result["retries"] == 1

    @pytest.mark.asyncio
    async def test_execute_max_retries_exceeded(
        self, engine: OrchestrationEngine, session: _FakeSession
    ) -> None:
        task = _make_task(session, state="queued")

        async def handler(ctx: TaskContext) -> str:
            raise ValueError("always fails")

        result = await engine.execute(task_id=task.id, handler=handler)
        assert result["state"] == "failed"
        assert result["retries"] > DEFAULT_MAX_RETRIES

    @pytest.mark.asyncio
    async def test_execute_task_not_found(
        self, engine: OrchestrationEngine, session: _FakeSession
    ) -> None:
        async def handler(ctx: TaskContext) -> str:
            return "done"

        with pytest.raises(TaskError) as exc:
            await engine.execute(task_id=uuid4(), handler=handler)
        assert exc.value.code == "task_not_found"

    @pytest.mark.asyncio
    async def test_execute_delegation_depth_exceeded(
        self, engine: OrchestrationEngine, session: _FakeSession
    ) -> None:
        task = _make_task(session, state="queued")

        async def handler(ctx: TaskContext) -> str:
            return "done"

        with pytest.raises(TaskError) as exc:
            await engine.execute(
                task_id=task.id,
                handler=handler,
                delegation_depth=MAX_DELEGATION_DEPTH + 1,
            )
        assert exc.value.code == "task_delegation_depth_exceeded"

    @pytest.mark.asyncio
    async def test_execute_already_completed(
        self, engine: OrchestrationEngine, session: _FakeSession
    ) -> None:
        task = _make_task(session, state="completed")

        async def handler(ctx: TaskContext) -> str:
            return "should-not-run"

        result = await engine.execute(task_id=task.id, handler=handler)
        assert result["state"] == "completed"
        assert result.get("cached") is True

    def test_valid_states(self) -> None:
        assert "queued" in VALID_STATES
        assert "running" in VALID_STATES
        assert "completed" in VALID_STATES
        assert "failed" in VALID_STATES
        assert "cancelled" in VALID_STATES
        assert "blocked" in VALID_STATES

    def test_validate_state_transition(self, engine: OrchestrationEngine) -> None:
        assert engine.validate_state_transition("queued", "running") is True
        assert engine.validate_state_transition("running", "completed") is True
        assert engine.validate_state_transition("completed", "running") is False
        assert engine.validate_state_transition("running", "cancelled") is True
