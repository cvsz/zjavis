"""Agent Runtime API endpoints.

Provides autonomous agent task execution.
Gated behind the agent_runtime_enabled configuration flag.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from jarvis.ai.agent_runtime import AgentRuntime
from jarvis.api.auth import get_current_user
from jarvis.auth import get_or_create_user_tenant, require_policy
from jarvis.core.config import settings
from jarvis.core.logging import get_logger
from jarvis.core.security import Permission
from jarvis.db import get_session
from jarvis.db.models import User

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/agent-runtime", tags=["agent-runtime"])


class TaskExecuteRequest(BaseModel):
    task_id: UUID


class TaskExecuteResponse(BaseModel):
    task_id: str
    state: str
    response: str | None
    provider: str | None
    model: str | None
    usage: dict[str, int]


@router.post("/execute", response_model=TaskExecuteResponse)
async def execute_task(
    request: TaskExecuteRequest,
    session: AsyncSession = Depends(get_session),  # noqa: B008
    _: None = Depends(
        require_policy(
            required_permission=Permission.REPOSITORY_WRITE,
            action="execute agent task",
            risk_level="medium",
        )
    ),
    authorization: str | None = None,
) -> TaskExecuteResponse:
    """Execute a task through the agent runtime."""
    user: User = await get_current_user(session, authorization)
    tenant = await get_or_create_user_tenant(session, user)
    runtime = AgentRuntime(session=session, enabled=settings.agent_runtime_enabled)
    try:
        result = await runtime.execute_task(
            request.task_id,
            tenant_id=tenant.id,
            user_id=user.id,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=str(exc)
        )
    return TaskExecuteResponse(
        task_id=result["task_id"],
        state=result["state"],
        response=result.get("response"),
        provider=result.get("provider"),
        model=result.get("model"),
        usage=result.get("usage", {}),
    )
