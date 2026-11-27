"""Unit tests for the JARVIS agent runtime."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from jarvis.ai.agent_runtime import AgentRuntime
from jarvis.core.exceptions import NotFoundError


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
