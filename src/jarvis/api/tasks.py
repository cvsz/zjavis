"""Task API endpoints.

Provides CRUD operations for tasks with tenant isolation.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from jarvis.api.auth import get_current_user
from jarvis.core.exceptions import NotFoundError
from jarvis.core.logging import get_logger
from jarvis.db import get_session
from jarvis.db.models import Task

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/tasks", tags=["tasks"])


class TaskCreate(BaseModel):
    task_type: str = Field(..., min_length=1, max_length=100)
    risk_classification: str = Field(default="low", max_length=50)
    agent_id: UUID | None = None
    idempotency_key: str | None = Field(default=None, max_length=255)


class TaskUpdate(BaseModel):
    task_type: str | None = Field(default=None, min_length=1, max_length=100)
    risk_classification: str | None = Field(default=None, max_length=50)
    agent_id: UUID | None = None
    state: str | None = Field(default=None, max_length=50)
    idempotency_key: str | None = Field(default=None, max_length=255)


class TaskResponse(BaseModel):
    id: str
    tenant_id: str
    user_id: str
    agent_id: str | None
    task_type: str
    risk_classification: str
    state: str
    idempotency_key: str | None
    started_at: str | None
    completed_at: str | None
    retry_count: int
    error_message: str | None


@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    request: TaskCreate,
    session: AsyncSession = Depends(get_session),  # noqa: B008
    authorization: str | None = None,
) -> TaskResponse:
    """Create a new task."""
    user = await get_current_user(session, authorization)
    task = Task(
        tenant_id=user.id,
        user_id=user.id,
        task_type=request.task_type,
        risk_classification=request.risk_classification,
        agent_id=request.agent_id,
        idempotency_key=request.idempotency_key,
    )
    session.add(task)
    await session.commit()
    await session.refresh(task)
    logger.info("Task created", extra={"task_id": str(task.id)})
    return TaskResponse(
        id=str(task.id),
        tenant_id=str(task.tenant_id),
        user_id=str(task.user_id),
        agent_id=str(task.agent_id) if task.agent_id else None,
        task_type=task.task_type,
        risk_classification=task.risk_classification,
        state=task.state,
        idempotency_key=task.idempotency_key,
        started_at=str(task.started_at) if task.started_at else None,
        completed_at=str(task.completed_at) if task.completed_at else None,
        retry_count=task.retry_count,
        error_message=task.error_message,
    )


@router.get("", response_model=list[TaskResponse])
async def list_tasks(
    session: AsyncSession = Depends(get_session),  # noqa: B008
    authorization: str | None = None,
    state: str | None = None,
    task_type: str | None = None,
    limit: int = 50,
) -> list[TaskResponse]:
    """List tasks for the authenticated user."""
    user = await get_current_user(session, authorization)
    query = select(Task).where(Task.user_id == user.id)
    if state is not None:
        query = query.where(Task.state == state)
    if task_type is not None:
        query = query.where(Task.task_type == task_type)
    query = query.limit(limit)
    result = await session.execute(query)
    tasks = result.scalars().all()
    return [
        TaskResponse(
            id=str(t.id),
            tenant_id=str(t.tenant_id),
            user_id=str(t.user_id),
            agent_id=str(t.agent_id) if t.agent_id else None,
            task_type=t.task_type,
            risk_classification=t.risk_classification,
            state=t.state,
            idempotency_key=t.idempotency_key,
            started_at=str(t.started_at) if t.started_at else None,
            completed_at=str(t.completed_at) if t.completed_at else None,
            retry_count=t.retry_count,
            error_message=t.error_message,
        )
        for t in tasks
    ]


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: UUID,
    session: AsyncSession = Depends(get_session),  # noqa: B008
    authorization: str | None = None,
) -> TaskResponse:
    """Get a single task by ID."""
    user = await get_current_user(session, authorization)
    result = await session.execute(
        select(Task).where(Task.id == task_id, Task.user_id == user.id)
    )
    task = result.scalar_one_or_none()
    if task is None:
        raise NotFoundError(f"Task not found: {task_id}")
    return TaskResponse(
        id=str(task.id),
        tenant_id=str(task.tenant_id),
        user_id=str(task.user_id),
        agent_id=str(task.agent_id) if task.agent_id else None,
        task_type=task.task_type,
        risk_classification=task.risk_classification,
        state=task.state,
        idempotency_key=task.idempotency_key,
        started_at=str(task.started_at) if task.started_at else None,
        completed_at=str(task.completed_at) if task.completed_at else None,
        retry_count=task.retry_count,
        error_message=task.error_message,
    )


@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: UUID,
    request: TaskUpdate,
    session: AsyncSession = Depends(get_session),  # noqa: B008
    authorization: str | None = None,
) -> TaskResponse:
    """Update a task."""
    user = await get_current_user(session, authorization)
    result = await session.execute(
        select(Task).where(Task.id == task_id, Task.user_id == user.id)
    )
    task = result.scalar_one_or_none()
    if task is None:
        raise NotFoundError(f"Task not found: {task_id}")

    if request.task_type is not None:
        task.task_type = request.task_type
    if request.risk_classification is not None:
        task.risk_classification = request.risk_classification
    if request.agent_id is not None:
        task.agent_id = request.agent_id
    if request.state is not None:
        task.state = request.state
    if request.idempotency_key is not None:
        task.idempotency_key = request.idempotency_key

    await session.commit()
    await session.refresh(task)
    logger.info("Task updated", extra={"task_id": str(task.id)})
    return TaskResponse(
        id=str(task.id),
        tenant_id=str(task.tenant_id),
        user_id=str(task.user_id),
        agent_id=str(task.agent_id) if task.agent_id else None,
        task_type=task.task_type,
        risk_classification=task.risk_classification,
        state=task.state,
        idempotency_key=task.idempotency_key,
        started_at=str(task.started_at) if task.started_at else None,
        completed_at=str(task.completed_at) if task.completed_at else None,
        retry_count=task.retry_count,
        error_message=task.error_message,
    )


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: UUID,
    session: AsyncSession = Depends(get_session),  # noqa: B008
    authorization: str | None = None,
) -> None:
    """Delete a task."""
    user = await get_current_user(session, authorization)
    result = await session.execute(
        select(Task).where(Task.id == task_id, Task.user_id == user.id)
    )
    task = result.scalar_one_or_none()
    if task is None:
        raise NotFoundError(f"Task not found: {task_id}")
    await session.delete(task)
    await session.commit()
    logger.info("Task deleted", extra={"task_id": str(task_id)})
