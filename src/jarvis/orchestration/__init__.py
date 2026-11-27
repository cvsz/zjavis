"""Task orchestration layer.

Provides durable, bounded task execution with state management,
retry logic, cancellation, and recovery coordination.

Per javis-blueprint.md sections 3.4 and 8.3, all task execution must be:
- Bounded (absolute deadlines, per-step timeouts)
- Retryable with exponential backoff and jitter
- Cancellable (cancellation propagation)
- Idempotent (idempotency keys for mutating operations)
- Recoverable (durable checkpoints, dead-letter handling)
- Free of infinite loops or recursive delegation
"""

from __future__ import annotations

import asyncio
import secrets
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select as _sa_select

from jarvis.core.exceptions import TaskError
from jarvis.core.logging import get_logger
from jarvis.db.models import Task

logger = get_logger(__name__)

# Default execution bounds
DEFAULT_MAX_RUNTIME_SECONDS = 300
DEFAULT_MAX_RETRIES = 3
DEFAULT_BASE_BACKOFF_SECONDS = 1.0
DEFAULT_MAX_BACKOFF_SECONDS = 60.0
DEFAULT_MAX_TOOL_CALLS = 50
MAX_DELEGATION_DEPTH = 5

# Valid task states
VALID_STATES: frozenset[str] = frozenset(
    {"queued", "running", "blocked", "completed", "failed", "cancelled"}
)

# Allowed state transitions: from_state -> set of allowed to_states
_ALLOWED_TRANSITIONS: dict[str, frozenset[str]] = {
    "queued": frozenset({"running", "blocked", "cancelled"}),
    "running": frozenset({"completed", "failed", "blocked", "cancelled"}),
    "blocked": frozenset({"running", "cancelled"}),
    "completed": frozenset(),
    "failed": frozenset({"queued"}),  # retry
    "cancelled": frozenset(),
}


@dataclass
class TaskContext:
    """Runtime context for a single task execution."""

    task_id: uuid.UUID
    tenant_id: uuid.UUID | None
    user_id: uuid.UUID | None
    task_type: str
    risk_classification: str
    max_runtime_seconds: int
    max_tool_calls: int
    idempotency_key: str | None = None
    retry_count: int = 0
    state: str = "queued"
    error_message: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    delegation_depth: int = 0
    cancelled: bool = field(default=False, init=False)
    _deadline: datetime | None = field(default=None, init=False)

    @property
    def deadline(self) -> datetime | None:
        return self._deadline

    @deadline.setter
    def deadline(self, value: datetime | None) -> None:
        self._deadline = value

    @property
    def is_expired(self) -> bool:
        if self._deadline is None:
            return False
        return datetime.now(UTC) >= self._deadline

    @property
    def remaining_seconds(self) -> float | None:
        if self._deadline is None:
            return None
        delta = self._deadline - datetime.now(UTC)
        return max(0.0, delta.total_seconds())

    def mark_cancelled(self) -> None:
        """Request cancellation. Checked by is_cancelled()."""
        self.cancelled = True

    @property
    def is_cancelled(self) -> bool:
        return self.cancelled

    def check_bounds(self) -> None:
        """Raise TaskError if the task has exceeded its bounds."""
        if self.is_cancelled:
            raise TaskError(
                f"Task {self.task_id} was cancelled",
                code="task_cancelled",
                details={"task_id": str(self.task_id)},
            )
        if self.is_expired:
            raise TaskError(
                f"Task {self.task_id} exceeded deadline",
                code="task_deadline_exceeded",
                details={"task_id": str(self.task_id)},
            )
        if self.retry_count > DEFAULT_MAX_RETRIES:
            raise TaskError(
                f"Task {self.task_id} exceeded max retries",
                code="task_max_retries_exceeded",
                details={"task_id": str(self.task_id), "retries": self.retry_count},
            )


class OrchestrationEngine:
    """Coordinates durable, bounded task execution.

    The engine manages the full task lifecycle:
    queued -> running -> completed/failed/cancelled/blocked.

    It enforces execution bounds (timeouts, retries, delegation depth)
    and records state transitions durably through the provided session.
    """

    def __init__(
        self,
        *,
        session: Any,
        max_runtime_seconds: int = DEFAULT_MAX_RUNTIME_SECONDS,
        max_retries: int = DEFAULT_MAX_RETRIES,
        base_backoff_seconds: float = DEFAULT_BASE_BACKOFF_SECONDS,
        max_backoff_seconds: float = DEFAULT_MAX_BACKOFF_SECONDS,
    ) -> None:
        self.session = session
        self.max_runtime_seconds = max_runtime_seconds
        self.max_retries = max_retries
        self.base_backoff_seconds = base_backoff_seconds
        self.max_backoff_seconds = max_backoff_seconds
        self._active_tasks: dict[uuid.UUID, TaskContext] = {}
        self._locks: dict[uuid.UUID, asyncio.Lock] = {}

    def _lock_for(self, task_id: uuid.UUID) -> asyncio.Lock:
        lock = self._locks.get(task_id)
        if lock is None:
            lock = asyncio.Lock()
            self._locks[task_id] = lock
        return lock

    @staticmethod
    def _context_from_model(task: Task) -> TaskContext:
        return TaskContext(
            task_id=task.id,
            tenant_id=task.tenant_id,
            user_id=task.user_id,
            task_type=task.task_type,
            risk_classification=task.risk_classification,
            max_runtime_seconds=int(
                getattr(task, "max_runtime_seconds", DEFAULT_MAX_RUNTIME_SECONDS)
                or DEFAULT_MAX_RUNTIME_SECONDS
            ),
            max_tool_calls=int(
                getattr(task, "max_tool_calls", DEFAULT_MAX_TOOL_CALLS)
                or DEFAULT_MAX_TOOL_CALLS
            ),
            idempotency_key=task.idempotency_key,
            retry_count=int(task.retry_count) if task.retry_count is not None else 0,
            state=task.state,
            error_message=task.error_message,
            started_at=task.started_at,
            completed_at=task.completed_at,
        )

    async def _load_task(self, task_id: uuid.UUID) -> Task:
        result = await self.session.execute(_sa_select(Task).where(Task.id == task_id))
        task = result.scalar_one_or_none()
        if task is None:
            raise TaskError(
                f"Task {task_id} not found in database",
                code="task_not_found",
                details={"task_id": str(task_id)},
            )
        return task

    async def _persist_context(self, ctx: TaskContext) -> None:
        task = await self._load_task(ctx.task_id)
        from_state = str(task.state) if task.state is not None else ""
        to_state = ctx.state
        if from_state and not self.validate_state_transition(from_state, to_state):
            raise TaskError(
                f"Invalid state transition {from_state} -> {to_state} for task {ctx.task_id}",
                code="invalid_state_transition",
                details={
                    "task_id": str(ctx.task_id),
                    "from_state": from_state,
                    "to_state": to_state,
                },
            )
        task.state = ctx.state
        task.retry_count = ctx.retry_count
        task.error_message = ctx.error_message
        if ctx.started_at is not None:
            task.started_at = ctx.started_at
        if ctx.completed_at is not None:
            task.completed_at = ctx.completed_at
        await self.session.commit()

    def _backoff_seconds(self, retry_count: int) -> float:
        """Exponential backoff with jitter."""
        backoff = min(
            self.base_backoff_seconds * (2.0 ** (retry_count - 1)),
            self.max_backoff_seconds,
        )
        # Use secrets for jitter (security-safe randomness)
        jitter = backoff * (0.1 * secrets.randbelow(1000) / 1000.0)
        return backoff + jitter

    async def execute(
        self,
        *,
        task_id: uuid.UUID,
        handler: Callable[[TaskContext], Any],
        deadline: datetime | None = None,
        delegation_depth: int = 0,
    ) -> dict[str, Any]:
        """Execute a task with bounded retry, cancellation, and recovery.

        Args:
            task_id: The task to execute.
            handler: Async callable that performs the work. It receives
                a TaskContext and must check ctx.is_cancelled periodically.
            deadline: Absolute deadline for the task.
            delegation_depth: Current delegation depth (0 = top-level).

        Returns:
            Dict with execution result: state, response, error, retries.

        Raises:
            TaskError: If the task cannot be executed within bounds.
        """
        if delegation_depth > MAX_DELEGATION_DEPTH:
            raise TaskError(
                f"Task {task_id} exceeded max delegation depth",
                code="task_delegation_depth_exceeded",
                details={
                    "task_id": str(task_id),
                    "depth": delegation_depth,
                    "max_depth": MAX_DELEGATION_DEPTH,
                },
            )

        lock = self._lock_for(task_id)
        async with lock:
            # Load task from database
            task = await self._load_task(task_id)
            ctx = self._context_from_model(task)

            # Check if an active context exists and is cancelled
            active_ctx = self._active_tasks.get(task_id)
            if active_ctx is not None and active_ctx.is_cancelled:
                ctx.mark_cancelled()

            if deadline is not None:
                ctx.deadline = deadline
            elif ctx.deadline is None:
                ctx.deadline = datetime.now(UTC) + timedelta(
                    seconds=ctx.max_runtime_seconds
                )

            self._active_tasks[task_id] = ctx

            try:
                # Idempotency: if already completed, return cached result
                if ctx.state == "completed":
                    logger.info(
                        "Task already completed, returning cached result",
                        extra={"task_id": str(task_id)},
                    )
                    return {
                        "state": ctx.state,
                        "task_id": str(task_id),
                        "retries": ctx.retry_count,
                        "cached": True,
                    }

                if ctx.state == "cancelled":
                    return {
                        "state": ctx.state,
                        "task_id": str(task_id),
                        "retries": ctx.retry_count,
                        "cancelled": True,
                    }

                # Mark running
                ctx.state = "running"
                ctx.started_at = datetime.now(UTC)
                await self._persist_context(ctx)

                last_error: str | None = None
                while ctx.retry_count <= self.max_retries:
                    ctx.check_bounds()

                    try:
                        response = await handler(ctx)
                        ctx.state = "completed"
                        ctx.completed_at = datetime.now(UTC)
                        ctx.error_message = None
                        await self._persist_context(ctx)
                        logger.info(
                            "Task completed",
                            extra={
                                "task_id": str(task_id),
                                "retries": ctx.retry_count,
                            },
                        )
                        return {
                            "state": ctx.state,
                            "task_id": str(task_id),
                            "response": response,
                            "retries": ctx.retry_count,
                            "completed_at": ctx.completed_at.isoformat(),
                        }
                    except asyncio.CancelledError:
                        ctx.state = "cancelled"
                        ctx.completed_at = datetime.now(UTC)
                        await self._persist_context(ctx)
                        logger.warning(
                            "Task cancelled",
                            extra={"task_id": str(task_id)},
                        )
                        return {
                            "state": ctx.state,
                            "task_id": str(task_id),
                            "retries": ctx.retry_count,
                            "cancelled": True,
                        }
                    except TaskError as exc:
                        last_error = str(exc)
                        if exc.code in (
                            "task_cancelled",
                            "task_deadline_exceeded",
                            "task_max_retries_exceeded",
                        ):
                            ctx.state = "failed"
                            ctx.error_message = last_error
                            ctx.completed_at = datetime.now(UTC)
                            await self._persist_context(ctx)
                            return {
                                "state": ctx.state,
                                "task_id": str(task_id),
                                "error": last_error,
                                "retries": ctx.retry_count,
                            }
                        raise
                    except Exception as exc:  # noqa: BLE001 - handler errors are retried
                        last_error = str(exc)
                        ctx.retry_count += 1
                        if ctx.retry_count > self.max_retries:
                            ctx.state = "failed"
                            ctx.error_message = last_error
                            ctx.completed_at = datetime.now(UTC)
                            await self._persist_context(ctx)
                            logger.error(
                                "Task failed after max retries",
                                extra={
                                    "task_id": str(task_id),
                                    "retries": ctx.retry_count,
                                    "error": last_error,
                                },
                            )
                            return {
                                "state": ctx.state,
                                "task_id": str(task_id),
                                "error": last_error,
                                "retries": ctx.retry_count,
                            }
                        # Exponential backoff before retry
                        backoff = self._backoff_seconds(ctx.retry_count)
                        logger.warning(
                            "Task retrying after error",
                            extra={
                                "task_id": str(task_id),
                                "retry": ctx.retry_count,
                                "backoff_seconds": backoff,
                                "error": last_error,
                            },
                        )
                        await asyncio.sleep(backoff)

                # Should not reach here, but handle gracefully
                ctx.state = "failed"
                ctx.error_message = last_error or "Unknown error"
                ctx.completed_at = datetime.now(UTC)
                await self._persist_context(ctx)
                return {
                    "state": ctx.state,
                    "task_id": str(task_id),
                    "error": ctx.error_message,
                    "retries": ctx.retry_count,
                }
            finally:
                self._active_tasks.pop(task_id, None)

    async def cancel(self, task_id: uuid.UUID) -> bool:
        """Request cancellation of an active task.

        Returns True if the task was found (in active tasks or database)
        and cancellation was requested.
        """
        # Mark in active context if present
        ctx = self._active_tasks.get(task_id)
        if ctx is not None:
            ctx.mark_cancelled()
            logger.info(
                "Task cancellation requested (active)",
                extra={"task_id": str(task_id)},
            )
            return True

        # Persist cancellation to database for non-active tasks
        try:
            task = await self._load_task(task_id)
        except TaskError:
            return False

        if task.state in ("completed", "cancelled", "failed"):
            return False

        task.state = "cancelled"
        await self.session.commit()
        logger.info(
            "Task cancellation requested (database)",
            extra={"task_id": str(task_id)},
        )
        return True

    async def get_state(self, task_id: uuid.UUID) -> str | None:
        """Get the current state of a task."""
        ctx = self._active_tasks.get(task_id)
        if ctx is not None:
            return ctx.state
        task = await self._load_task(task_id)
        return str(task.state) if task.state is not None else None

    def validate_state_transition(self, from_state: str, to_state: str) -> bool:
        """Validate that a state transition is allowed."""
        return to_state in _ALLOWED_TRANSITIONS.get(from_state, frozenset())


__all__ = [
    "DEFAULT_MAX_BACKOFF_SECONDS",
    "DEFAULT_MAX_RETRIES",
    "DEFAULT_MAX_RUNTIME_SECONDS",
    "MAX_DELEGATION_DEPTH",
    "VALID_STATES",
    "OrchestrationEngine",
    "TaskContext",
    "TaskError",
]
