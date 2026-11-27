"""Bounded task execution engine.

Implements durable, bounded task execution with state management,
retry logic with exponential backoff and jitter, cancellation,
idempotency, dead-letter handling, and recovery coordination
per javis-blueprint.md §3.4 and §8.

All operations are timeout-bounded and safe under concurrent workers.
"""

from __future__ import annotations

import asyncio
import secrets
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, ParamSpec, TypeVar
from uuid import uuid4

from jarvis.core.exceptions import TaskError
from jarvis.core.logging import get_logger

logger = get_logger(__name__)

P = ParamSpec("P")
T = TypeVar("T")

# Default bounds (overridable per execution).
DEFAULT_TIMEOUT_SECONDS = 300
DEFAULT_MAX_RETRIES = 3
DEFAULT_BASE_BACKOFF_SECONDS = 1.0
DEFAULT_MAX_BACKOFF_SECONDS = 60.0
DEFAULT_JITTER_SECONDS = 0.5


@dataclass(frozen=True)
class ExecutionBounds:
    """Resource and time bounds for a single task execution."""

    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS
    max_retries: int = DEFAULT_MAX_RETRIES
    base_backoff_seconds: float = DEFAULT_BASE_BACKOFF_SECONDS
    max_backoff_seconds: float = DEFAULT_MAX_BACKOFF_SECONDS
    jitter_seconds: float = DEFAULT_JITTER_SECONDS
    idempotency_key: str | None = None


@dataclass
class ExecutionResult:
    """Outcome of a bounded task execution."""

    success: bool
    result: Any | None = None
    error: str | None = None
    error_type: str | None = None
    attempts: int = 0
    duration_seconds: float = 0.0
    cancelled: bool = False
    idempotency_key: str | None = None


@dataclass
class DeadLetterEntry:
    """A task execution that exhausted retries and was dead-lettered."""

    task_id: str
    error: str
    error_type: str
    attempts: int
    failed_at: datetime
    bounds: ExecutionBounds
    result: ExecutionResult | None = None


class CancellationToken:
    """Cooperative cancellation token shared across concurrent tasks."""

    def __init__(self) -> None:
        self._cancelled = False
        self._listeners: list[Callable[[], None]] = []

    @property
    def is_cancelled(self) -> bool:
        return self._cancelled

    def cancel(self) -> None:
        """Request cancellation. Notifies all registered listeners."""
        if self._cancelled:
            return
        self._cancelled = True
        for listener in self._listeners:
            try:
                listener()
            except Exception:
                logger.exception("Cancellation listener raised")

    def add_listener(self, listener: Callable[[], None]) -> None:
        """Register a listener to be notified on cancellation."""
        self._listeners.append(listener)

    def check(self) -> None:
        """Raise TaskError if cancellation has been requested."""
        if self._cancelled:
            raise TaskError("Task cancelled", code="cancelled")


class ExecutionEngine:
    """Executes an async callable within enforced bounds.

    Provides:
    - Per-execution timeout (asyncio.wait_for)
    - Retry with exponential backoff and jitter
    - Cooperative cancellation via CancellationToken
    - Idempotency key tracking (in-memory, per engine instance)
    - Dead-letter capture when retries are exhausted
    """

    def __init__(self, *, bounds: ExecutionBounds | None = None) -> None:
        self.bounds = bounds or ExecutionBounds()
        self._idempotency_records: dict[str, ExecutionResult] = {}
        self._dead_letters: list[DeadLetterEntry] = []
        self._lock = asyncio.Lock()
        self.logger = get_logger(__name__)

    def _compute_backoff(self, attempt: int) -> float:
        """Compute exponential backoff with jitter for a given attempt index."""
        backoff = min(
            self.bounds.base_backoff_seconds * (2**attempt),
            self.bounds.max_backoff_seconds,
        )
        # Use a cryptographically secure RNG for jitter (bandit B311: random
        # is not suitable for security purposes; jitter is a security-relevant
        # randomization here because it desynchronizes concurrent retries).
        jitter = secrets.SystemRandom().uniform(0.0, self.bounds.jitter_seconds)
        return float(backoff + jitter)

    async def _record_idempotency(self, key: str, result: ExecutionResult) -> None:
        """Store an idempotent result keyed by idempotency key."""
        async with self._lock:
            self._idempotency_records[key] = result

    async def _get_idempotency(self, key: str) -> ExecutionResult | None:
        async with self._lock:
            return self._idempotency_records.get(key)

    async def _record_dead_letter(self, entry: DeadLetterEntry) -> None:
        async with self._lock:
            self._dead_letters.append(entry)

    def dead_letters(self) -> list[DeadLetterEntry]:
        """Return all dead-letter entries recorded by this engine."""
        return list(self._dead_letters)

    def idempotency_keys(self) -> list[str]:
        """Return all recorded idempotency keys."""
        return list(self._idempotency_records.keys())

    async def execute(
        self,
        *,
        func: Callable[P, Awaitable[T]],
        args: tuple[Any, ...] = (),
        kwargs: dict[str, Any] | None = None,
        bounds: ExecutionBounds | None = None,
        cancellation: CancellationToken | None = None,
    ) -> ExecutionResult:
        """Execute ``func`` within enforced bounds.

        Args:
            func: Async callable to execute.
            args: Positional arguments for ``func``.
            kwargs: Keyword arguments for ``func``.
            bounds: Execution bounds (defaults to engine bounds).
            cancellation: Optional shared cancellation token.

        Returns:
            An :class:`ExecutionResult` describing the outcome.
        """
        effective_bounds = bounds or self.bounds
        kwargs = kwargs or {}
        cancel = cancellation or CancellationToken()
        start = time.monotonic()
        attempts = 0
        last_error: str | None = None
        last_error_type: str | None = None

        # Idempotency: return cached result if this key was already executed.
        if effective_bounds.idempotency_key:
            cached = await self._get_idempotency(effective_bounds.idempotency_key)
            if cached is not None:
                self.logger.info(
                    "Idempotent replay returning cached result",
                    extra={
                        "idempotency_key": effective_bounds.idempotency_key,
                        "cached_success": cached.success,
                    },
                )
                return cached

        while attempts <= effective_bounds.max_retries:
            attempts += 1
            try:
                cancel.check()
                result = await asyncio.wait_for(
                    func(*args, **kwargs),
                    timeout=effective_bounds.timeout_seconds,
                )
                duration = time.monotonic() - start
                exec_result = ExecutionResult(
                    success=True,
                    result=result,
                    attempts=attempts,
                    duration_seconds=duration,
                    idempotency_key=effective_bounds.idempotency_key,
                )
                if effective_bounds.idempotency_key:
                    await self._record_idempotency(
                        effective_bounds.idempotency_key, exec_result
                    )
                self.logger.info(
                    "Task execution succeeded",
                    extra={
                        "attempts": attempts,
                        "duration_seconds": round(duration, 4),
                        "idempotency_key": effective_bounds.idempotency_key,
                    },
                )
                return exec_result

            except asyncio.CancelledError:
                cancel.cancel()
                duration = time.monotonic() - start
                exec_result = ExecutionResult(
                    success=False,
                    error="Task cancelled",
                    error_type="CancelledError",
                    attempts=attempts,
                    duration_seconds=duration,
                    cancelled=True,
                    idempotency_key=effective_bounds.idempotency_key,
                )
                self.logger.warning(
                    "Task execution cancelled",
                    extra={
                        "attempts": attempts,
                        "idempotency_key": effective_bounds.idempotency_key,
                    },
                )
                return exec_result

            except TimeoutError:
                last_error = (
                    f"Execution timed out after {effective_bounds.timeout_seconds}s"
                )
                last_error_type = "TimeoutError"
                self.logger.warning(
                    "Task execution timed out",
                    extra={
                        "attempt": attempts,
                        "timeout_seconds": effective_bounds.timeout_seconds,
                        "idempotency_key": effective_bounds.idempotency_key,
                    },
                )
                if attempts > effective_bounds.max_retries:
                    break
                await asyncio.sleep(self._compute_backoff(attempts - 1))
                continue

            except TaskError as exc:
                last_error = str(exc) or "Task error"
                last_error_type = exc.code or "TaskError"
                if exc.code == "cancelled":
                    cancel.cancel()
                    duration = time.monotonic() - start
                    exec_result = ExecutionResult(
                        success=False,
                        error=last_error,
                        error_type=last_error_type,
                        attempts=attempts,
                        duration_seconds=duration,
                        cancelled=True,
                        idempotency_key=effective_bounds.idempotency_key,
                    )
                    self.logger.warning(
                        "Task execution cancelled by cooperative token",
                        extra={
                            "attempts": attempts,
                            "idempotency_key": effective_bounds.idempotency_key,
                        },
                    )
                    return exec_result
                # Non-cancellation TaskError is not retried (deterministic failure).
                break

            except Exception as exc:  # noqa: BLE001 - retryable unexpected error
                last_error = str(exc)
                last_error_type = type(exc).__name__
                self.logger.warning(
                    "Task execution attempt failed",
                    extra={
                        "attempt": attempts,
                        "error": last_error,
                        "error_type": last_error_type,
                        "idempotency_key": effective_bounds.idempotency_key,
                    },
                )
                if attempts > effective_bounds.max_retries:
                    break
                await asyncio.sleep(self._compute_backoff(attempts - 1))
                continue

        # Retries exhausted — dead-letter the failure.
        duration = time.monotonic() - start
        exec_result = ExecutionResult(
            success=False,
            error=last_error or "Unknown execution error",
            error_type=last_error_type or "UnknownError",
            attempts=attempts,
            duration_seconds=duration,
            idempotency_key=effective_bounds.idempotency_key,
        )
        dead_letter = DeadLetterEntry(
            task_id=str(uuid4()),
            error=last_error or "Unknown execution error",
            error_type=last_error_type or "UnknownError",
            attempts=attempts,
            failed_at=datetime.now(UTC),
            bounds=effective_bounds,
            result=exec_result,
        )
        await self._record_dead_letter(dead_letter)
        self.logger.error(
            "Task execution dead-lettered after exhausted retries",
            extra={
                "attempts": attempts,
                "error": last_error,
                "error_type": last_error_type,
                "duration_seconds": round(duration, 4),
                "idempotency_key": effective_bounds.idempotency_key,
                "dead_letter_id": dead_letter.task_id,
            },
        )
        return exec_result


__all__ = [
    "DEFAULT_BASE_BACKOFF_SECONDS",
    "DEFAULT_JITTER_SECONDS",
    "DEFAULT_MAX_BACKOFF_SECONDS",
    "DEFAULT_MAX_RETRIES",
    "DEFAULT_TIMEOUT_SECONDS",
    "CancellationToken",
    "DeadLetterEntry",
    "ExecutionBounds",
    "ExecutionEngine",
    "ExecutionResult",
]
