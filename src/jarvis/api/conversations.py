"""Conversation API endpoints.

Provides conversation and message CRUD operations with tenant isolation.
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
from jarvis.db.models import Conversation, Message

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/conversations", tags=["conversations"])


class ConversationCreate(BaseModel):
    title: str | None = Field(default=None, max_length=500)


class ConversationResponse(BaseModel):
    id: str
    tenant_id: str
    user_id: str
    title: str | None
    is_archived: bool


class MessageCreate(BaseModel):
    role: str = Field(..., min_length=1, max_length=50)
    content: str = Field(..., min_length=1)


class MessageResponse(BaseModel):
    id: str
    conversation_id: str
    role: str
    content: str
    token_count: int | None


@router.post("", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    request: ConversationCreate,
    session: AsyncSession = Depends(get_session),  # noqa: B008
    authorization: str | None = None,
) -> ConversationResponse:
    """Create a new conversation for the authenticated user."""
    user = await get_current_user(session, authorization)
    conversation = Conversation(
        tenant_id=UUID("00000000-0000-0000-0000-000000000000"),
        user_id=user.id,
        title=request.title,
    )
    session.add(conversation)
    await session.commit()
    await session.refresh(conversation)
    logger.info("Conversation created", extra={"conversation_id": str(conversation.id)})
    return ConversationResponse(
        id=str(conversation.id),
        tenant_id=str(conversation.tenant_id),
        user_id=str(conversation.user_id),
        title=conversation.title,  # type: ignore[arg-type]
        is_archived=conversation.is_archived,  # type: ignore[arg-type]
    )


@router.get("", response_model=list[ConversationResponse])
async def list_conversations(
    session: AsyncSession = Depends(get_session),  # noqa: B008
    authorization: str | None = None,
) -> list[ConversationResponse]:
    """List conversations for the authenticated user."""
    user = await get_current_user(session, authorization)
    result = await session.execute(
        select(Conversation).where(Conversation.user_id == user.id)
    )
    conversations = result.scalars().all()
    return [
        ConversationResponse(
            id=str(c.id),
            tenant_id=str(c.tenant_id),
            user_id=str(c.user_id),
            title=c.title,  # type: ignore[arg-type]
            is_archived=c.is_archived,  # type: ignore[arg-type]
        )
        for c in conversations
    ]


@router.post(
    "/{conversation_id}/messages",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_message(
    conversation_id: UUID,
    request: MessageCreate,
    session: AsyncSession = Depends(get_session),  # noqa: B008
    authorization: str | None = None,
) -> MessageResponse:
    """Add a message to a conversation."""
    user = await get_current_user(session, authorization)
    result = await session.execute(
        select(Conversation).where(
            Conversation.id == conversation_id, Conversation.user_id == user.id
        )
    )
    conversation = result.scalar_one_or_none()
    if conversation is None:
        raise NotFoundError(f"Conversation not found: {conversation_id}")
    message = Message(
        conversation_id=conversation_id,
        role=request.role,
        content=request.content,
    )
    session.add(message)
    await session.commit()
    await session.refresh(message)
    logger.info(
        "Message created",
        extra={"message_id": str(message.id), "conversation_id": str(conversation_id)},
    )
    return MessageResponse(
        id=str(message.id),
        conversation_id=str(message.conversation_id),
        role=message.role,  # type: ignore[arg-type]
        content=message.content,  # type: ignore[arg-type]
        token_count=message.token_count,  # type: ignore[arg-type]
    )
