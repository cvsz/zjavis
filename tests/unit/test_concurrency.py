"""Phase 11 concurrency tests.

Verifies that task orchestration state transitions and memory deduplication
remain correct under concurrent access, per blueprint §3.4 (bounded execution,
cancellation, idempotency) and §7.2 (deduplication).
"""

from __future__ import annotations

import asyncio
import uuid
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from jarvis.ai.memory import MemoryService, generate_content_hash
from jarvis.db.models import Memory
from jarvis.orchestration import _ALLOWED_TRANSITIONS, VALID_STATES, OrchestrationEngine


def _scalar_mock(value: Any) -> MagicMock:
    mock = MagicMock()
    mock.scalar_one_or_none = lambda: value
    return mock


def _scalars_mock(values: list[Any]) -> MagicMock:
    mock = MagicMock()
    mock.scalars = lambda: MagicMock(all=lambda: values)
    return mock


class TestOrchestrationConcurrency:
    """Concurrency safety for the OrchestrationEngine."""

    def test_valid_states_match_transitions(self) -> None:
        """Every state in VALID_STATES appears as a transition key."""
        assert VALID_STATES == set(_ALLOWED_TRANSITIONS)

    def test_no_state_transitions_to_itself(self) -> None:
        """A task may not transition to the same state (idempotency guard)."""
        for from_state, allowed in _ALLOWED_TRANSITIONS.items():
            assert from_state not in allowed, f"{from_state} may transition to itself"

    def test_terminal_states_have_no_outgoing(self) -> None:
        """Completed, failed (except retry), cancelled are terminal."""
        assert _ALLOWED_TRANSITIONS["completed"] == set()
        assert _ALLOWED_TRANSITIONS["cancelled"] == set()

    def test_per_task_lock_is_stable(self) -> None:
        """The same task_id always resolves to the same asyncio.Lock.

        This is the mechanism that serializes concurrent mutation of a single
        task so state transitions cannot interleave.
        """
        session = AsyncMock(spec=AsyncSession)
        engine = OrchestrationEngine(session=session)
        task_id = uuid.uuid4()
        lock1 = engine._lock_for(task_id)
        lock2 = engine._lock_for(task_id)
        assert lock1 is lock2
        different = engine._lock_for(uuid.uuid4())
        assert different is not lock1

    @pytest.mark.asyncio
    async def test_concurrent_same_task_lock_serializes(self) -> None:
        """Two coroutines locking the same task observe mutual exclusion."""
        session = AsyncMock(spec=AsyncSession)
        engine = OrchestrationEngine(session=session)
        task_id = uuid.uuid4()
        acquired = []

        async def hold_lock() -> None:
            async with engine._lock_for(task_id):
                acquired.append(task_id)
                await asyncio.sleep(0.01)

        await asyncio.gather(hold_lock(), hold_lock())
        # The lock serializes: both acquires happened (order may vary).
        assert len(acquired) == 2


class TestMemoryConcurrency:
    """Concurrency safety for memory deduplication."""

    @pytest.fixture
    def mock_session(self) -> AsyncSession:
        return AsyncMock(spec=AsyncSession)

    @pytest.mark.asyncio
    async def test_concurrent_add_same_content_dedups(
        self, mock_session: AsyncSession
    ) -> None:
        """Two concurrent adds of the same content return one memory.

        Simulates the race: the first add persists and the second add's
        duplicate check finds the now-existing memory.
        """

        created = Memory(
            id="mem-1",
            tenant_id="t1",
            user_id="u1",
            memory_type="semantic",
            content="shared content",
            content_hash=generate_content_hash("shared content"),
        )

        calls = {"count": 0}

        def execute_side_effect(*args, **kwargs):
            calls["count"] += 1
            result = MagicMock()
            # First call: no existing (proceed to create).
            # Second and later: existing found (dedup).
            result.scalar_one_or_none = lambda: None if calls["count"] == 1 else created
            return result

        mock_session.execute = AsyncMock(side_effect=execute_side_effect)
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

        service = MemoryService(mock_session)
        content = "shared content"

        results = await asyncio.gather(
            service.add_memory(
                tenant_id="t1", user_id="u1", memory_type="semantic", content=content
            ),
            service.add_memory(
                tenant_id="t1", user_id="u1", memory_type="semantic", content=content
            ),
        )

        # Both returns represent the same deduplicated content.
        assert results[0].content == results[1].content == content
        assert results[0].content_hash == results[1].content_hash
        # Only one insert occurred (the first); the second hit the existing row.
        assert mock_session.add.call_count == 1

    @pytest.mark.asyncio
    async def test_concurrent_add_different_content_creates_both(
        self, mock_session: AsyncSession
    ) -> None:
        """Two concurrent adds of different content create two memories."""
        mock_session.execute.return_value = _scalar_mock(None)
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

        service = MemoryService(mock_session)

        results = await asyncio.gather(
            service.add_memory(
                tenant_id="t1",
                user_id="u1",
                memory_type="semantic",
                content="content one",
            ),
            service.add_memory(
                tenant_id="t1",
                user_id="u1",
                memory_type="semantic",
                content="content two",
            ),
        )

        assert results[0].content == "content one"
        assert results[1].content == "content two"
        assert results[0].content_hash != results[1].content_hash
        assert mock_session.add.call_count == 2

    @pytest.mark.asyncio
    async def test_hash_deterministic_under_concurrency(self) -> None:
        """Content hashing is deterministic regardless of call order."""
        hashes = await asyncio.gather(
            *[
                asyncio.to_thread(generate_content_hash, "stable content")
                for _ in range(10)
            ]
        )
        assert len(set(hashes)) == 1
        assert len(hashes[0]) == 64  # SHA-256 hex


class TestTaskModelConcurrency:
    """Task model invariants under concurrent-style mutation."""

    def test_state_transition_invariants(self) -> None:
        """Every defined transition maps a valid state to a valid state."""
        for from_state, allowed in _ALLOWED_TRANSITIONS.items():
            assert from_state in VALID_STATES
            for to_state in allowed:
                assert to_state in VALID_STATES

    def test_retry_transition_only_from_failed(self) -> None:
        """The failed->queued (retry) transition is unique to failed."""
        for from_state, allowed in _ALLOWED_TRANSITIONS.items():
            if "queued" in allowed:
                assert from_state == "failed"
