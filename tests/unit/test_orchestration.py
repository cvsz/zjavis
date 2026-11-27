"""Unit tests for the bounded task execution engine (orchestration).

Covers success, retry, timeout, cancellation, idempotency replay,
dead-letter capture, and backoff bound computation.
"""

from __future__ import annotations

import asyncio
import uuid
from typing import Any, TypeVar

import pytest

from jarvis.core.exceptions import TaskError
from jarvis.orchestration import (
    CancellationToken,
    DeadLetterEntry,
    ExecutionBounds,
    ExecutionEngine,
)

T = TypeVar("T")


class TrackingFunc:
    """Callable wrapper that records how many times it was invoked."""

    def __init__(self) -> None:
        self.calls = 0

    async def __call__(self, *args: Any, **kwargs: Any) -> Any:
        self.calls += 1
        return self._invoke(*args, **kwargs)

    def _invoke(self, *args: Any, **kwargs: Any) -> Any:
        raise NotImplementedError


class SucceedFunc(TrackingFunc):
    def __init__(self, value: Any = "ok") -> None:
        super().__init__()
        self._value = value

    def _invoke(self, *args: Any, **kwargs: Any) -> Any:
        return self._value


class FailThenSucceedFunc(TrackingFunc):
    def __init__(self, succeed_on_attempt: int, value: Any = "recovered") -> None:
        super().__init__()
        self._succeed_on_attempt = succeed_on_attempt
        self._value = value

    def _invoke(self, *args: Any, **kwargs: Any) -> Any:
        if self.calls < self._succeed_on_attempt:
            raise ValueError("simulated failure")
        return self._value


class AlwaysFailFunc(TrackingFunc):
    def __init__(self, exc: type[Exception] = RuntimeError) -> None:
        super().__init__()
        self._exc = exc

    def _invoke(self, *args: Any, **kwargs: Any) -> Any:
        raise self._exc("simulated failure")


class SlowFunc(TrackingFunc):
    async def _invoke(self, *args: Any, **kwargs: Any) -> Any:
        await asyncio.sleep(10)
        return "too-late"


class CancelFunc(TrackingFunc):
    def __init__(self, cancel: CancellationToken) -> None:
        super().__init__()
        self._cancel = cancel

    def _invoke(self, *args: Any, **kwargs: Any) -> Any:
        self._cancel.check()
        return "never"


class PermanentTaskErrorFunc(TrackingFunc):
    def _invoke(self, *args: Any, **kwargs: Any) -> Any:
        raise TaskError("permanent failure", code="permanent")


@pytest.mark.asyncio
async def test_execution_succeeds_first_attempt() -> None:
    engine = ExecutionEngine(bounds=ExecutionBounds(timeout_seconds=10, max_retries=3))
    func = SucceedFunc("done")
    result: Any = await engine.execute(func=func)
    assert result.success is True
    assert result.result == "done"
    assert result.attempts == 1
    assert result.cancelled is False
    assert result.error is None


@pytest.mark.asyncio
async def test_execution_retries_then_succeeds() -> None:
    engine = ExecutionEngine(
        bounds=ExecutionBounds(
            timeout_seconds=10, max_retries=3, base_backoff_seconds=0
        )
    )
    func = FailThenSucceedFunc(succeed_on_attempt=3)
    result: Any = await engine.execute(func=func)
    assert result.success is True
    assert result.result == "recovered"
    assert result.attempts == 3


@pytest.mark.asyncio
async def test_execution_exhausts_retries_and_dead_letters() -> None:
    engine = ExecutionEngine(
        bounds=ExecutionBounds(
            timeout_seconds=10, max_retries=2, base_backoff_seconds=0
        )
    )
    func = AlwaysFailFunc(RuntimeError)
    result: Any = await engine.execute(func=func)
    assert result.success is False
    assert result.attempts == 3  # initial + 2 retries
    assert "simulated failure" in (result.error or "")
    assert result.error_type == "RuntimeError"
    dead = engine.dead_letters()
    assert len(dead) == 1
    assert isinstance(dead[0], DeadLetterEntry)
    assert dead[0].error_type == "RuntimeError"
    assert dead[0].attempts == 3


@pytest.mark.asyncio
async def test_execution_timeout_dead_letters() -> None:
    engine = ExecutionEngine(
        bounds=ExecutionBounds(timeout_seconds=0, max_retries=1, base_backoff_seconds=0)
    )
    func = SlowFunc()
    result: Any = await engine.execute(func=func)
    assert result.success is False
    assert result.error_type == "TimeoutError"
    assert result.attempts == 2  # initial + 1 retry
    dead = engine.dead_letters()
    assert len(dead) == 1
    assert dead[0].error_type == "TimeoutError"


@pytest.mark.asyncio
async def test_cancellation_token_stops_execution() -> None:
    cancel = CancellationToken()
    engine = ExecutionEngine(
        bounds=ExecutionBounds(
            timeout_seconds=30, max_retries=3, base_backoff_seconds=0
        )
    )
    func = CancelFunc(cancel)
    cancel.cancel()
    result: Any = await engine.execute(func=func, cancellation=cancel)
    assert result.success is False
    assert result.cancelled is True
    assert result.error_type == "cancelled"
    assert result.error == "Task cancelled"


@pytest.mark.asyncio
async def test_idempotency_key_returns_cached_result() -> None:
    key = f"idem-{uuid.uuid4().hex[:8]}"
    engine = ExecutionEngine(
        bounds=ExecutionBounds(timeout_seconds=10, max_retries=0, idempotency_key=key)
    )
    func = SucceedFunc("first")
    first: Any = await engine.execute(func=func)
    assert first.success is True
    assert first.result == "first"

    replay: Any = await engine.execute(func=func)
    assert replay.success is True
    assert replay.result == "first"
    assert func.calls == 1  # func not re-invoked


@pytest.mark.asyncio
async def test_idempotency_keys_accessor() -> None:
    engine = ExecutionEngine(bounds=ExecutionBounds())
    k1 = f"idem-{uuid.uuid4().hex[:8]}"
    k2 = f"idem-{uuid.uuid4().hex[:8]}"
    await engine.execute(
        func=SucceedFunc("a"), bounds=ExecutionBounds(idempotency_key=k1)
    )
    await engine.execute(
        func=SucceedFunc("b"), bounds=ExecutionBounds(idempotency_key=k2)
    )
    keys = engine.idempotency_keys()
    assert k1 in keys
    assert k2 in keys


@pytest.mark.asyncio
async def test_backoff_within_bounds() -> None:
    engine = ExecutionEngine(
        bounds=ExecutionBounds(
            base_backoff_seconds=1.0,
            max_backoff_seconds=5.0,
            jitter_seconds=0.0,
        )
    )
    b0 = engine._compute_backoff(0)
    b1 = engine._compute_backoff(1)
    b2 = engine._compute_backoff(2)
    b3 = engine._compute_backoff(3)  # 8.0 -> capped at max_backoff_seconds
    assert 0.9 <= b0 <= 1.1
    assert 1.9 <= b1 <= 2.1
    assert 3.9 <= b2 <= 4.1
    assert 4.9 <= b3 <= 5.1  # capped at max_backoff_seconds


@pytest.mark.asyncio
async def test_task_error_non_cancelled_not_retried() -> None:
    engine = ExecutionEngine(
        bounds=ExecutionBounds(
            timeout_seconds=10, max_retries=3, base_backoff_seconds=0
        )
    )
    func = PermanentTaskErrorFunc()
    result: Any = await engine.execute(func=func)
    assert result.success is False
    assert result.attempts == 1  # not retried
    assert result.error_type == "permanent"


@pytest.mark.asyncio
async def test_default_bounds_are_sensible() -> None:
    bounds = ExecutionBounds()
    assert bounds.timeout_seconds == 300
    assert bounds.max_retries == 3
    assert bounds.base_backoff_seconds == 1.0
    assert bounds.max_backoff_seconds == 60.0
    assert bounds.jitter_seconds == 0.5
