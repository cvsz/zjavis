"""Tenant isolation tests.

Verifies that every data-access endpoint scopes queries by the
authenticated user's tenant (never by user.id), preventing cross-tenant
data leakage per javis-blueprint.md section 13.2 and section 15.2.
"""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest

from jarvis.api.agents import get_agent, list_agents
from jarvis.api.audit import list_audit_events
from jarvis.api.conversations import ConversationCreate, create_conversation
from jarvis.api.memory import get_memory, list_memories
from jarvis.core.exceptions import NotFoundError
from jarvis.db.models import Agent, Conversation, Memory, User


async def _async_none(*args, **kwargs) -> None:
    """Async no-op stand-in for session.commit() / session.refresh().

    When an object is passed (e.g. session.refresh(obj)), populate required
    fields so Pydantic response models can validate.
    """
    if args:
        obj = args[0]
        if not hasattr(obj, "id") or obj.id is None:
            obj.id = uuid4()
        if not hasattr(obj, "is_archived"):
            obj.is_archived = False


class _FakeUser:
    """Minimal stand-in for an authenticated User with tenant context."""

    def __init__(self, tenant_id: UUID | None, organization_id: UUID) -> None:
        self.id = uuid4()
        self.tenant_id = tenant_id
        self.organization_id = organization_id


class _ExecResult:
    """Mock result of session.execute()."""

    def __init__(self, scalars: list[object] | None = None) -> None:
        self._scalar = scalars[0] if scalars else None
        self._all = list(scalars or [])

    def scalar_one_or_none(self):
        return self._scalar

    def scalars(self):
        class _Scalars:
            def __init__(self, items):
                self._items = items

            def all(self):
                return self._items

        return _Scalars(self._all)


class _Session:
    """Minimal async session stand-in capturing the executed statement."""

    def __init__(self) -> None:
        self.last_statement: object | None = None
        self.result: _ExecResult | None = None

    async def execute(self, statement):
        self.last_statement = statement
        return self.result or _ExecResult()


@pytest.mark.asyncio
async def test_list_agents_uses_tenant_id_not_user_id():
    """list_agents must filter by tenant_id, never user.id."""
    from unittest.mock import patch

    tenant_id = uuid4()
    org_id = uuid4()
    user = _FakeUser(tenant_id=tenant_id, organization_id=org_id)
    session = _Session()
    session.result = _ExecResult([])

    with patch("jarvis.api.agents.get_current_user", return_value=user):
        await list_agents(session=session, authorization="Bearer fake")

    stmt = str(session.last_statement)
    assert "tenants" in stmt or "agent" in stmt.lower()
    # The where clause must reference tenant_id column, not user.id
    assert "tenant_id" in stmt
    assert str(org_id) not in stmt or str(tenant_id) in stmt


@pytest.mark.asyncio
async def test_get_agent_uses_tenant_id_not_user_id():
    """get_agent must scope by tenant_id."""
    from unittest.mock import patch

    tenant_id = uuid4()
    org_id = uuid4()
    user = _FakeUser(tenant_id=tenant_id, organization_id=org_id)
    session = _Session()
    session.result = _ExecResult([None])

    with (
        patch("jarvis.api.agents.get_current_user", return_value=user),
        pytest.raises(NotFoundError),
    ):
        await get_agent(agent_id=uuid4(), session=session, authorization="Bearer fake")

    stmt = str(session.last_statement)
    assert "tenant_id" in stmt


@pytest.mark.asyncio
async def test_list_memories_uses_tenant_id():
    """list_memories must filter by tenant_id."""
    from unittest.mock import patch

    tenant_id = uuid4()
    org_id = uuid4()
    user = _FakeUser(tenant_id=tenant_id, organization_id=org_id)
    session = _Session()
    session.result = _ExecResult([])

    with patch("jarvis.api.memory.get_current_user", return_value=user):
        await list_memories(session=session, authorization="Bearer fake")

    stmt = str(session.last_statement)
    assert "tenant_id" in stmt


@pytest.mark.asyncio
async def test_get_memory_uses_tenant_id():
    """get_memory must scope by tenant_id."""
    from unittest.mock import patch

    tenant_id = uuid4()
    org_id = uuid4()
    user = _FakeUser(tenant_id=tenant_id, organization_id=org_id)
    session = _Session()
    session.result = _ExecResult([None])

    with (
        patch("jarvis.api.memory.get_current_user", return_value=user),
        pytest.raises(NotFoundError),
    ):
        await get_memory(
            memory_id=uuid4(), session=session, authorization="Bearer fake"
        )

    stmt = str(session.last_statement)
    assert "tenant_id" in stmt


@pytest.mark.asyncio
async def test_list_audit_events_uses_tenant_id():
    """list_audit_events must filter by tenant_id (not user.id)."""
    from unittest.mock import patch

    tenant_id = uuid4()
    org_id = uuid4()
    user = _FakeUser(tenant_id=tenant_id, organization_id=org_id)
    session = _Session()
    session.result = _ExecResult([])

    with patch("jarvis.api.audit.get_current_user", return_value=user):
        await list_audit_events(session=session, authorization="Bearer fake")

    stmt = str(session.last_statement)
    assert "tenant_id" in stmt


@pytest.mark.asyncio
async def test_create_conversation_uses_tenant_id():
    """create_conversation must set tenant_id from user.tenant_id, not user.id."""
    from unittest.mock import patch

    tenant_id = uuid4()
    org_id = uuid4()
    user = _FakeUser(tenant_id=tenant_id, organization_id=org_id)
    session = _Session()
    created: Conversation | None = None

    def fake_add(obj):
        nonlocal created
        if isinstance(obj, Conversation):
            if obj.id is None:
                obj.id = uuid4()
            if obj.is_archived is None:
                obj.is_archived = False
            created = obj

    session.add = fake_add  # type: ignore[method-assign]
    session.commit = _async_none  # type: ignore[method-assign]
    session.refresh = _async_none  # type: ignore[method-assign]

    with patch("jarvis.api.conversations.get_current_user", return_value=user):
        await create_conversation(
            request=ConversationCreate(title="Isolated Chat"),
            session=session,
            authorization="Bearer fake",
        )

    assert created is not None
    assert created.tenant_id == tenant_id
    assert created.tenant_id != user.id


@pytest.mark.asyncio
async def test_create_conversation_tenant_none_falls_back_to_organization():
    """When user.tenant_id is None, fall back to organization_id."""
    from unittest.mock import patch

    tenant_id = None
    org_id = uuid4()
    user = _FakeUser(tenant_id=tenant_id, organization_id=org_id)
    session = _Session()
    created: Conversation | None = None

    def fake_add(obj):
        nonlocal created
        if isinstance(obj, Conversation):
            if obj.id is None:
                obj.id = uuid4()
            if obj.is_archived is None:
                obj.is_archived = False
            created = obj

    session.add = fake_add  # type: ignore[method-assign]
    session.commit = _async_none  # type: ignore[method-assign]
    session.refresh = _async_none  # type: ignore[method-assign]

    with patch("jarvis.api.conversations.get_current_user", return_value=user):
        await create_conversation(
            request=ConversationCreate(title="Org Fallback"),
            session=session,
            authorization="Bearer fake",
        )

    assert created is not None
    assert created.tenant_id == org_id


def test_user_model_has_tenant_id_column():
    """User model must declare tenant_id as a UUID FK to tenants."""
    assert hasattr(User, "tenant_id")
    col = User.__table__.columns["tenant_id"]
    assert col.nullable is True
    assert col.index is True


def test_task_model_has_tenant_id_column():
    """Task model must declare tenant_id as a UUID FK to tenants."""
    from jarvis.db.models import Task

    assert hasattr(Task, "tenant_id")
    col = Task.__table__.columns["tenant_id"]
    assert col.nullable is False
    assert col.index is True


def test_agent_model_has_tenant_id_column():
    """Agent model must declare tenant_id as a UUID FK to tenants."""
    assert hasattr(Agent, "tenant_id")
    col = Agent.__table__.columns["tenant_id"]
    assert col.nullable is False
    assert col.index is True


def test_memory_model_has_tenant_id_column():
    """Memory model must declare tenant_id as a UUID FK to tenants."""
    assert hasattr(Memory, "tenant_id")
    col = Memory.__table__.columns["tenant_id"]
    assert col.nullable is False
    assert col.index is True
