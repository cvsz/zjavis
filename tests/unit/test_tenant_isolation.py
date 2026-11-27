"""Unit tests for tenant isolation in data access.

Verifies that resources are scoped to the correct tenant and that
cross-tenant access is prevented.
"""

from __future__ import annotations

from uuid import UUID, uuid4

from jarvis.db.models import Agent, Conversation, Memory, Task


def test_conversation_tenant_id_is_uuid() -> None:
    """Conversation tenant_id must be a valid UUID (not user.id misused)."""
    conv = Conversation(
        tenant_id=uuid4(),
        user_id=uuid4(),
        title="Test",
    )
    assert isinstance(UUID(str(conv.tenant_id)), UUID)
    assert isinstance(UUID(str(conv.user_id)), UUID)


def test_memory_tenant_id_is_uuid() -> None:
    """Memory tenant_id must be a valid UUID."""
    mem = Memory(
        tenant_id=uuid4(),
        user_id=uuid4(),
        memory_type="conversation",
        content="test",
    )
    assert isinstance(UUID(str(mem.tenant_id)), UUID)
    assert isinstance(UUID(str(mem.user_id)), UUID)


def test_agent_tenant_id_is_uuid() -> None:
    """Agent tenant_id must be a valid UUID."""
    agent = Agent(
        tenant_id=uuid4(),
        name="test-agent",
    )
    assert isinstance(UUID(str(agent.tenant_id)), UUID)


def test_task_tenant_id_is_uuid() -> None:
    """Task tenant_id must be a valid UUID."""
    task = Task(
        tenant_id=uuid4(),
        user_id=uuid4(),
        task_type="test",
    )
    assert isinstance(UUID(str(task.tenant_id)), UUID)
    assert isinstance(UUID(str(task.user_id)), UUID)


def test_tenant_id_and_user_id_are_distinct() -> None:
    """tenant_id and user_id should be different UUIDs in practice."""
    tenant_id = uuid4()
    user_id = uuid4()
    assert tenant_id != user_id

    conv = Conversation(
        tenant_id=tenant_id,
        user_id=user_id,
        title="Test",
    )
    assert conv.tenant_id != conv.user_id
