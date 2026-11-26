"""Agent API endpoints.

Provides CRUD operations for agent definitions with tenant isolation.
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
from jarvis.db.models import Agent

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/agents", tags=["agents"])


class AgentCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    version: str = Field(default="1.0.0", max_length=50)
    description: str | None = None
    max_runtime_seconds: int = Field(default=300, ge=1)
    max_tool_calls: int = Field(default=50, ge=1)


class AgentUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    version: str | None = Field(default=None, max_length=50)
    description: str | None = None
    is_active: bool | None = None
    max_runtime_seconds: int | None = Field(default=None, ge=1)
    max_tool_calls: int | None = Field(default=None, ge=1)


class AgentResponse(BaseModel):
    id: str
    tenant_id: str
    name: str
    version: str
    description: str | None
    is_active: bool
    max_runtime_seconds: int
    max_tool_calls: int


@router.post("", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
async def create_agent(
    request: AgentCreate,
    session: AsyncSession = Depends(get_session),  # noqa: B008
    authorization: str | None = None,
) -> AgentResponse:
    """Create a new agent definition."""
    user = await get_current_user(session, authorization)
    agent = Agent(
        tenant_id=user.id,
        name=request.name,
        version=request.version,
        description=request.description,
        max_runtime_seconds=request.max_runtime_seconds,
        max_tool_calls=request.max_tool_calls,
    )
    session.add(agent)
    await session.commit()
    await session.refresh(agent)
    logger.info("Agent created", extra={"agent_id": str(agent.id)})
    return AgentResponse(
        id=str(agent.id),
        tenant_id=str(agent.tenant_id),
        name=agent.name,  # type: ignore[arg-type]
        version=agent.version,  # type: ignore[arg-type]
        description=agent.description,  # type: ignore[arg-type]
        is_active=agent.is_active,  # type: ignore[arg-type]
        max_runtime_seconds=agent.max_runtime_seconds,  # type: ignore[arg-type]
        max_tool_calls=agent.max_tool_calls,  # type: ignore[arg-type]
    )


@router.get("", response_model=list[AgentResponse])
async def list_agents(
    session: AsyncSession = Depends(get_session),  # noqa: B008
    authorization: str | None = None,
    is_active: bool | None = None,
    limit: int = 50,
) -> list[AgentResponse]:
    """List agents for the authenticated user's tenant."""
    user = await get_current_user(session, authorization)
    query = select(Agent).where(Agent.tenant_id == user.id)
    if is_active is not None:
        query = query.where(Agent.is_active == is_active)
    query = query.limit(limit)
    result = await session.execute(query)
    agents = result.scalars().all()
    return [
        AgentResponse(
            id=str(a.id),
            tenant_id=str(a.tenant_id),
            name=a.name,  # type: ignore[arg-type]
            version=a.version,  # type: ignore[arg-type]
            description=a.description,  # type: ignore[arg-type]
            is_active=a.is_active,  # type: ignore[arg-type]
            max_runtime_seconds=a.max_runtime_seconds,  # type: ignore[arg-type]
            max_tool_calls=a.max_tool_calls,  # type: ignore[arg-type]
        )
        for a in agents
    ]


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: UUID,
    session: AsyncSession = Depends(get_session),  # noqa: B008
    authorization: str | None = None,
) -> AgentResponse:
    """Get a single agent by ID."""
    user = await get_current_user(session, authorization)
    result = await session.execute(
        select(Agent).where(Agent.id == agent_id, Agent.tenant_id == user.id)
    )
    agent = result.scalar_one_or_none()
    if agent is None:
        raise NotFoundError(f"Agent not found: {agent_id}")
    return AgentResponse(
        id=str(agent.id),
        tenant_id=str(agent.tenant_id),
        name=agent.name,  # type: ignore[arg-type]
        version=agent.version,  # type: ignore[arg-type]
        description=agent.description,  # type: ignore[arg-type]
        is_active=agent.is_active,  # type: ignore[arg-type]
        max_runtime_seconds=agent.max_runtime_seconds,  # type: ignore[arg-type]
        max_tool_calls=agent.max_tool_calls,  # type: ignore[arg-type]
    )


@router.put("/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_id: UUID,
    request: AgentUpdate,
    session: AsyncSession = Depends(get_session),  # noqa: B008
    authorization: str | None = None,
) -> AgentResponse:
    """Update an agent definition."""
    user = await get_current_user(session, authorization)
    result = await session.execute(
        select(Agent).where(Agent.id == agent_id, Agent.tenant_id == user.id)
    )
    agent = result.scalar_one_or_none()
    if agent is None:
        raise NotFoundError(f"Agent not found: {agent_id}")

    if request.name is not None:
        agent.name = request.name  # type: ignore[assignment]
    if request.version is not None:
        agent.version = request.version  # type: ignore[assignment]
    if request.description is not None:
        agent.description = request.description  # type: ignore[assignment]
    if request.is_active is not None:
        agent.is_active = request.is_active  # type: ignore[assignment]
    if request.max_runtime_seconds is not None:
        agent.max_runtime_seconds = request.max_runtime_seconds  # type: ignore[assignment]
    if request.max_tool_calls is not None:
        agent.max_tool_calls = request.max_tool_calls  # type: ignore[assignment]

    await session.commit()
    await session.refresh(agent)
    logger.info("Agent updated", extra={"agent_id": str(agent.id)})
    return AgentResponse(
        id=str(agent.id),
        tenant_id=str(agent.tenant_id),
        name=agent.name,  # type: ignore[arg-type]
        version=agent.version,  # type: ignore[arg-type]
        description=agent.description,  # type: ignore[arg-type]
        is_active=agent.is_active,  # type: ignore[arg-type]
        max_runtime_seconds=agent.max_runtime_seconds,  # type: ignore[arg-type]
        max_tool_calls=agent.max_tool_calls,  # type: ignore[arg-type]
    )


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agent(
    agent_id: UUID,
    session: AsyncSession = Depends(get_session),  # noqa: B008
    authorization: str | None = None,
) -> None:
    """Delete an agent definition."""
    user = await get_current_user(session, authorization)
    result = await session.execute(
        select(Agent).where(Agent.id == agent_id, Agent.tenant_id == user.id)
    )
    agent = result.scalar_one_or_none()
    if agent is None:
        raise NotFoundError(f"Agent not found: {agent_id}")
    await session.delete(agent)
    await session.commit()
    logger.info("Agent deleted", extra={"agent_id": str(agent_id)})
