"""Conversation API endpoints.

Provides conversation and message CRUD operations with tenant isolation.
Integrates with the AI model gateway for AI responses.
"""

from __future__ import annotations

import json
from uuid import UUID

from fastapi import APIRouter, Depends, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from jarvis.ai.gateway import gateway
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


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    task_type: str = Field(default="default", max_length=50)
    stream: bool = Field(default=False)


class ChatResponse(BaseModel):
    conversation_id: str
    user_message_id: str
    assistant_message_id: str
    response: str
    usage: dict[str, int]


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


@router.post(
    "/{conversation_id}/chat",
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK,
)
async def chat(
    conversation_id: UUID,
    request: ChatRequest,
    session: AsyncSession = Depends(get_session),  # noqa: B008
    authorization: str | None = None,
) -> ChatResponse:
    """Send a message and get an AI response.

    Creates a user message, then generates an AI response using the
    model gateway. Returns both messages with the AI response.
    """
    user = await get_current_user(session, authorization)

    result = await session.execute(
        select(Conversation).where(
            Conversation.id == conversation_id, Conversation.user_id == user.id
        )
    )
    conversation = result.scalar_one_or_none()
    if conversation is None:
        raise NotFoundError(f"Conversation not found: {conversation_id}")

    # Create user message
    user_message = Message(
        conversation_id=conversation_id,
        role="user",
        content=request.message,
    )
    session.add(user_message)
    await session.commit()
    await session.refresh(user_message)

    # Build conversation context from recent messages
    result = await session.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.desc())
        .limit(10)
    )
    recent_messages = result.scalars().all()
    recent_messages.reverse()  # Chronological order

    # Build messages for model gateway
    messages = [
        {"role": m.role, "content": m.content} for m in recent_messages
    ]

    # Call model gateway
    result = await gateway.complete(
        task_type=request.task_type,
        messages=messages,
    )

    # Create assistant message
    assistant_message = Message(
        conversation_id=conversation_id,
        role="assistant",
        content=result["response"],
        token_count=result.get("usage", {}).get("total_tokens"),
    )
    session.add(assistant_message)
    await session.commit()
    await session.refresh(assistant_message)

    logger.info(
        "Conversation message exchanged",
        extra={
            "conversation_id": str(conversation_id),
            "user_message_id": str(user_message.id),
            "assistant_message_id": str(assistant_message.id),
            "provider": result.get("provider"),
            "model": result.get("model"),
        },
    )

    return ChatResponse(
        conversation_id=str(conversation_id),
        user_message_id=str(user_message.id),
        assistant_message_id=str(assistant_message.id),
        response=result["response"],
        usage=result.get("usage", {}),
    )


@router.post(
    "/{conversation_id}/chat/stream",
    status_code=status.HTTP_200_OK,
)
async def chat_stream(
    conversation_id: UUID,
    request: ChatRequest,
    session: AsyncSession = Depends(get_session),  # noqa: B008
    authorization: str | None = None,
):
    """Send a message and get a streaming AI response.

    Creates a user message, then streams the AI response using the
    model gateway's streaming capability.
    """
    user = await get_current_user(session, authorization)

    result = await session.execute(
        select(Conversation).where(
            Conversation.id == conversation_id, Conversation.user_id == user.id
        )
    )
    conversation = result.scalar_one_or_none()
    if conversation is None:
        raise NotFoundError(f"Conversation not found: {conversation_id}")

    # Create user message
    user_message = Message(
        conversation_id=conversation_id,
        role="user",
        content=request.message,
    )
    session.add(user_message)
    await session.commit()
    await session.refresh(user_message)

    # Build conversation context
    result_msgs = await session.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.desc())
        .limit(10)
    )
    recent_messages = result_msgs.scalars().all()
    recent_messages.reverse()

    messages = [
        {"role": m.role, "content": m.content} for m in recent_messages
    ]

    async def stream_generator():
        """Stream AI response chunks and save complete response."""
        full_response = ""
        try:
            async for chunk in gateway.complete_stream(
                task_type=request.task_type,
                messages=messages,
            ):
                content = chunk.get("content", "")
                if content:
                    full_response += content
                    yield f"data: {json.dumps({'content': content, 'done': False})}\n\n"
        except Exception as exc:  # noqa: BLE001 - catch all streaming errors gracefully
            logger.error(
                "Streaming error",
                extra={"conversation_id": str(conversation_id), "error": str(exc)},
            )
            yield f"data: {json.dumps({'error': str(exc), 'done': True})}\n\n"
            return

        # Save assistant message after streaming
        assistant_message = Message(
            conversation_id=conversation_id,
            role="assistant",
            content=full_response,
        )
        session.add(assistant_message)
        await session.commit()
        await session.refresh(assistant_message)

        logger.info(
            "Streaming conversation complete",
            extra={
                "conversation_id": str(conversation_id),
                "user_message_id": str(user_message.id),
                "assistant_message_id": str(assistant_message.id),
            },
        )

        yield f"data: {json.dumps({'content': '', 'done': True, 'message_id': str(assistant_message.id)})}\n\n"

    return StreamingResponse(
        stream_generator(),
        media_type="text/event-stream",
    )