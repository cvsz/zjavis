"""Unit tests for the JARVIS agent runtime."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from jarvis.ai.agent_runtime import AgentRuntime
from jarvis.core.exceptions import AuthorizationError, NotFoundError
from jarvis.db.models import Task


class TestAgentRuntime:
    """Tests for AgentRuntime."""

    @pytest.fixture
    def mock_session(self) -> AsyncSession:
        return AsyncMock(spec=AsyncSession)

    @pytest.fixture
    def runtime(self, mock_session: AsyncSession) -> AgentRuntime:
        return AgentRuntime(session=mock_session, enabled=True)

    @pytest.mark.asyncio
    async def test_execute_task_disabled(self, mock_session: AsyncSession) -> None:
        runtime = AgentRuntime(session=mock_session, enabled=False)
        import uuid

        with pytest.raises(RuntimeError, match="Agent runtime is disabled"):
            await runtime.execute_task(uuid.uuid4())

    @pytest.mark.asyncio
    async def test_execute_task_not_found(self, runtime: AgentRuntime) -> None:
        import uuid

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        runtime.session.execute.return_value = mock_result

        with pytest.raises(NotFoundError):
            await runtime.execute_task(uuid.uuid4())

    @pytest.mark.asyncio
    async def test_requires_approval_medium_risk(self, runtime: AgentRuntime) -> None:
        from jarvis.db.models import Task

        task = Task(
            id="task-1",
            tenant_id="t1",
            user_id="u1",
            task_type="test",
            risk_classification="medium",
        )
        result = await runtime._requires_approval(task)
        assert result is True

    @pytest.mark.asyncio
    async def test_requires_approval_low_risk(self, runtime: AgentRuntime) -> None:
        from jarvis.db.models import Task

        task = Task(
            id="task-1",
            tenant_id="t1",
            user_id="u1",
            task_type="test",
            risk_classification="low",
        )
        result = await runtime._requires_approval(task)
        assert result is False

    def test_uuid_conversion(self, runtime: AgentRuntime) -> None:
        import uuid

        uid = uuid.uuid4()
        result = runtime._uuid(uid)
        assert result == uid

        result = runtime._uuid(None)
        assert result is None

    @pytest.mark.asyncio
    async def test_is_approved_no_session(self, runtime: AgentRuntime) -> None:
        from unittest.mock import MagicMock

        task = MagicMock()
        task.id = None
        result = await runtime._is_approved(task)
        assert result is False

    @pytest.mark.asyncio
    async def test_execute_task_tenant_isolation_violation(
        self, runtime: AgentRuntime
    ) -> None:
        """execute_task must reject a task that belongs to a different tenant."""
        import uuid

        wrong_tenant = uuid.uuid4()
        task = Task(
            id=uuid.uuid4(),
            tenant_id=wrong_tenant,
            user_id=uuid.uuid4(),
            task_type="test",
            risk_classification="low",
        )
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = task
        runtime.session.execute.return_value = mock_result

        with pytest.raises(AuthorizationError) as exc:
            await runtime.execute_task(
                task.id, tenant_id=uuid.uuid4(), user_id=task.user_id
            )
        assert exc.value.code == "tenant_isolation_violation"

    @pytest.mark.asyncio
    async def test_execute_task_user_ownership_violation(
        self, runtime: AgentRuntime
    ) -> None:
        """execute_task must reject a task that belongs to a different user."""
        import uuid

        task = Task(
            id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            task_type="test",
            risk_classification="low",
        )
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = task
        runtime.session.execute.return_value = mock_result

        with pytest.raises(AuthorizationError) as exc:
            await runtime.execute_task(
                task.id, tenant_id=task.tenant_id, user_id=uuid.uuid4()
            )
        assert exc.value.code == "user_ownership_violation"

    @pytest.mark.asyncio
    async def test_execute_task_matching_tenant_and_user_passes(
        self, runtime: AgentRuntime
    ) -> None:
        """execute_task proceeds when tenant_id and user_id match the task."""
        import uuid

        tenant_id = uuid.uuid4()
        user_id = uuid.uuid4()
        task = Task(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            user_id=user_id,
            task_type="test",
            risk_classification="low",
            state="queued",
        )
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = task
        runtime.session.execute.return_value = mock_result

        # Approval not required for low risk; orchestration engine will be
        # invoked. Mock the engine to avoid real execution.
        from unittest.mock import AsyncMock, patch

        fake_engine = AsyncMock()
        fake_engine.execute.return_value = {
            "state": "completed",
            "task_id": str(task.id),
            "response": "ok",
            "retries": 0,
        }
        with patch(
            "jarvis.ai.agent_runtime.OrchestrationEngine", return_value=fake_engine
        ):
            result = await runtime.execute_task(
                task.id, tenant_id=tenant_id, user_id=user_id
            )
        assert result["state"] == "completed"
        assert result["response"] == "ok"
