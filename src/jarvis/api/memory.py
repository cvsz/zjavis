"""Memory API endpoints.

Provides CRUD and search operations for memory items with tenant isolation.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from jarvis.ai.memory import MemoryService
from jarvis.api.auth import get_current_user
from jarvis.core.exceptions import NotFoundError
from jarvis.core.logging import get_logger
from jarvis.db import get_session
from jarvis.db.models import Memory, Message

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/memory", tags=["memory"])


class MemoryCreate(BaseModel):
    memory_type: str = Field(default="conversation", max_length=50)
    content: str = Field(..., min_length=1)
    source: str | None = None
    source_type: str | None = Field(default=None, max_length=50)
    source_id: str | None = None
    confidence: int | None = Field(default=None, ge=0, le=100)
    expires_at: str | None = None


class MemoryResponse(BaseModel):
    id: str
    tenant_id: str
    user_id: str
    memory_type: str
    content: str
    source: str | None
    source_type: str | None
    source_id: str | None
    confidence: int | None
    expires_at: str | None
    is_deleted: bool
    created_at: str
    updated_at: str


@router.post("", response_model=MemoryResponse, status_code=status.HTTP_201_CREATED)
async def create_memory(
    request: MemoryCreate,
    session: AsyncSession = Depends(get_session),  # noqa: B008
    authorization: str | None = None,
) -> MemoryResponse:
    """Create a new memory item."""
    user = await get_current_user(session, authorization)
    service = MemoryService(session)
    memory = await service.add_memory(
        tenant_id=str(user.id),
        user_id=str(user.id),
        memory_type=request.memory_type,
        content=request.content,
        source=request.source,
        source_type=request.source_type,
        source_id=request.source_id,
        confidence=request.confidence,
        expires_at=request.expires_at,
    )
    return MemoryResponse(
        id=str(memory.id),
        tenant_id=str(memory.tenant_id),
        user_id=str(memory.user_id),
        memory_type=memory.memory_type,
        content=memory.content,
        source=memory.source,
        source_type=memory.source_type,
        source_id=memory.source_id,
        confidence=memory.confidence,
        expires_at=str(memory.expires_at) if memory.expires_at else None,
        is_deleted=memory.is_deleted,
        created_at=str(memory.created_at),
        updated_at=str(memory.updated_at),
    )


@router.get("", response_model=list[MemoryResponse])
async def list_memories(
    session: AsyncSession = Depends(get_session),  # noqa: B008
    authorization: str | None = None,
    memory_type: str | None = None,
    limit: int = 50,
) -> list[MemoryResponse]:
    """List memories for the authenticated user."""
    user = await get_current_user(session, authorization)
    service = MemoryService(session)
    memories = await service.search_memories(
        tenant_id=str(user.id),
        memory_type=memory_type,
        limit=limit,
    )
    return [
        MemoryResponse(
            id=str(m.id),
            tenant_id=str(m.tenant_id),
            user_id=str(m.user_id),
            memory_type=m.memory_type,
            content=m.content,
            source=m.source,
            source_type=m.source_type,
            source_id=m.source_id,
            confidence=m.confidence,
            expires_at=str(m.expires_at) if m.expires_at else None,
            is_deleted=m.is_deleted,
            created_at=str(m.created_at),
            updated_at=str(m.updated_at),
        )
        for m in memories
    ]


@router.get("/{memory_id}", response_model=MemoryResponse)
async def get_memory(
    memory_id: UUID,
    session: AsyncSession = Depends(get_session),  # noqa: B008
    authorization: str | None = None,
) -> MemoryResponse:
    """Get a single memory by ID."""
    user = await get_current_user(session, authorization)
    service = MemoryService(session)
    memory = await service.get_memory(str(memory_id), str(user.id))
    if memory is None:
        raise NotFoundError(f"Memory not found: {memory_id}")
    return MemoryResponse(
        id=str(memory.id),
        tenant_id=str(memory.tenant_id),
        user_id=str(memory.user_id),
        memory_type=memory.memory_type,
        content=memory.content,
        source=memory.source,
        source_type=memory.source_type,
        source_id=memory.source_id,
        confidence=memory.confidence,
        expires_at=str(memory.expires_at) if memory.expires_at else None,
        is_deleted=memory.is_deleted,
        created_at=str(memory.created_at),
        updated_at=str(memory.updated_at),
    )


@router.delete("/{memory_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_memory(
    memory_id: UUID,
    session: AsyncSession = Depends(get_session),  # noqa: B008
    authorization: str | None = None,
) -> None:
    """Soft-delete a memory item."""
    user = await get_current_user(session, authorization)
    service = MemoryService(session)
    deleted = await service.delete_memory(str(memory_id), str(user.id))
    if not deleted:
        raise NotFoundError(f"Memory not found: {memory_id}")


@router.post("/{conversation_id}/summarize", response_model=MemoryResponse)
async def summarize_conversation(
    conversation_id: UUID,
    session: AsyncSession = Depends(get_session),  # noqa: B008
    authorization: str | None = None,
) -> MemoryResponse:
    """Summarize a conversation into a memory item."""
    user = await get_current_user(session, authorization)
    result = await session.execute(
        select(Message).where(
            Message.conversation_id == conversation_id
        ).order_by(Message.created_at.asc())
    )
    messages = result.scalars().all()
    if not messages:
        raise NotFoundError(f"Conversation not found: {conversation_id}")

    # Build conversation text
    parts = []
    for m in messages:
        parts.append(f"{m.role}: {m.content}")
    content = "\n".join(parts)

    # Create memory from conversation summary
    memory = Memory(
        tenant_id=str(user.id),
        user_id=str(user.id),
        memory_type="conversation",
        content=f"Conversation summary: {content[:2000]}",
        source="conversation",
        source_type="conversation",
        source_id=str(conversation_id),
        confidence=80,
    )
    session.add(memory)
    await session.commit()
    await session.refresh(memory)

    return MemoryResponse(
        id=str(memory.id),
        tenant_id=str(memory.tenant_id),
        user_id=str(memory.user_id),
        memory_type=memory.memory_type,
        content=memory.content,
        source=memory.source,
        source_type=memory.source_type,
        source_id=memory.source_id,
        confidence=memory.confidence,
        expires_at=str(memory.expires_at) if memory.expires_at else None,
        is_deleted=memory.is_deleted,
        created_at=str(memory.created_at),
        updated_at=str(memory.updated_at),
    )


@router.get("/{conversation_id}/search", response_model=list[MemoryResponse])
async def search_memory(
    conversation_id: UUID,
    query: str,
    session: AsyncSession = Depends(get_session),  # noqa: B008
    authorization: str | None = None,
    limit: int = 10,
) -> list[MemoryResponse]:
    """Search memory within a conversation."""
    user = await get_current_user(session, authorization)
    service = MemoryService(session)
    memories = await service.search_memories(
        tenant_id=str(user.id),
        memory_type="conversation",
        query=query,
        limit=limit,
    )
    return [
        MemoryResponse(
            id=str(m.id),
            tenant_id=str(m.tenant_id),
            user_id=str(m.user_id),
            memory_type=m.memory_type,
            content=m.content,
            source=m.source,
            source_type=m.source_type,
            source_id=m.source_id,
            confidence=m.confidence,
            expires_at=str(m.expires_at) if m.expires_at else None,
            is_deleted=m.is_deleted,
            created_at=str(m.created_at),
            updated_at=str(m.updated_at),
        )
        for m in memories
    ]
