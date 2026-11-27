"""Database models for core entities.

Defines SQLAlchemy models for the JARVIS data architecture per
javis-blueprint.md section 13.1. All entities use UUID primary keys
and tenant-aware constraints where applicable.
"""

from __future__ import annotations

import uuid

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from jarvis.db.session import Base


class TimestampMixin:
    """Mixin providing created_at and updated_at timestamps."""

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class Organization(Base, TimestampMixin):
    """Organizations represent top-level tenants in the system."""

    __tablename__ = "organizations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, unique=True)
    slug = Column(String(255), nullable=False, unique=True, index=True)
    is_active = Column(Boolean, default=True, nullable=False)

    users = relationship(
        "User", back_populates="organization", cascade="all, delete-orphan"
    )
    tenants = relationship(
        "Tenant", back_populates="organization", cascade="all, delete-orphan"
    )


class User(Base, TimestampMixin):
    """Users are authenticated principals within an organization."""

    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    email = Column(String(255), nullable=False, index=True)
    username = Column(String(255), nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_superuser = Column(Boolean, default=False, nullable=False)

    __table_args__ = (
        UniqueConstraint("organization_id", "email", name="uq_user_org_email"),
        UniqueConstraint("organization_id", "username", name="uq_user_org_username"),
    )

    organization = relationship("Organization", back_populates="users")
    sessions = relationship(
        "Session", back_populates="user", cascade="all, delete-orphan"
    )
    role_bindings = relationship(
        "RoleBinding", back_populates="user", cascade="all, delete-orphan"
    )


class Tenant(Base, TimestampMixin):
    """Tenants provide data isolation boundaries."""

    __tablename__ = "tenants"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = Column(String(255), nullable=False)
    slug = Column(String(255), nullable=False, index=True)
    is_active = Column(Boolean, default=True, nullable=False)

    __table_args__ = (
        UniqueConstraint("organization_id", "slug", name="uq_tenant_org_slug"),
    )

    organization = relationship("Organization", back_populates="tenants")
    conversations = relationship(
        "Conversation", back_populates="tenant", cascade="all, delete-orphan"
    )
    tasks = relationship("Task", back_populates="tenant", cascade="all, delete-orphan")


class Role(Base, TimestampMixin):
    """Roles define named permission sets."""

    __tablename__ = "roles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, unique=True)
    description = Column(Text, nullable=True)

    role_bindings = relationship(
        "RoleBinding", back_populates="role", cascade="all, delete-orphan"
    )


class Permission(Base, TimestampMixin):
    """Permissions are atomic capability grants."""

    __tablename__ = "permissions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, unique=True)
    description = Column(Text, nullable=True)


class RoleBinding(Base, TimestampMixin):
    """RoleBindings assign roles to users within a tenant scope."""

    __tablename__ = "role_bindings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role_id = Column(
        UUID(as_uuid=True),
        ForeignKey("roles.id", ondelete="CASCADE"),
        nullable=False,
    )
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    __table_args__ = (
        UniqueConstraint("user_id", "role_id", "tenant_id", name="uq_user_role_tenant"),
    )

    user = relationship("User", back_populates="role_bindings")
    role = relationship("Role", back_populates="role_bindings")
    tenant = relationship("Tenant")


class Session(Base, TimestampMixin):
    """User sessions for authentication state management."""

    __tablename__ = "sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    token_hash = Column(String(255), nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    is_revoked = Column(Boolean, default=False, nullable=False)

    user = relationship("User", back_populates="sessions")
    tenant = relationship("Tenant")


class Conversation(Base, TimestampMixin):
    """Conversations represent chat sessions between users and JARVIS."""

    __tablename__ = "conversations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title = Column(String(500), nullable=True)
    is_archived = Column(Boolean, default=False, nullable=False)

    tenant = relationship("Tenant", back_populates="conversations")
    messages = relationship(
        "Message", back_populates="conversation", cascade="all, delete-orphan"
    )


class Message(Base, TimestampMixin):
    """Messages within a conversation."""

    __tablename__ = "messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role = Column(String(50), nullable=False)  # user, assistant, system, tool
    content = Column(Text, nullable=False)
    token_count = Column(Integer, nullable=True)

    conversation = relationship("Conversation", back_populates="messages")


class Memory(Base, TimestampMixin):
    """Persisted memory items with ownership and provenance."""

    __tablename__ = "memories"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    memory_type = Column(
        String(50), nullable=False
    )  # working, conversation, episodic, semantic, procedural, project, preference
    content = Column(Text, nullable=False)
    content_hash = Column(
        String(64), nullable=True, index=True
    )  # SHA-256 hash for deduplication
    source = Column(String(255), nullable=True)
    source_type = Column(
        String(50), nullable=True
    )  # document, web, conversation, email, etc.
    source_id = Column(
        String(255), nullable=True, index=True
    )  # External source identifier
    confidence = Column(Integer, nullable=True)  # 0-100
    expires_at = Column(DateTime(timezone=True), nullable=True)
    is_deleted = Column(Boolean, default=False, nullable=False)


class Agent(Base, TimestampMixin):
    """Agent definitions with capability declarations."""

    __tablename__ = "agents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = Column(String(255), nullable=False)
    version = Column(String(50), nullable=False, default="1.0.0")
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    max_runtime_seconds = Column(Integer, default=300, nullable=False)
    max_tool_calls = Column(Integer, default=50, nullable=False)


class Task(Base, TimestampMixin):
    """Tasks represent units of work executed by agents or the core."""

    __tablename__ = "tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    agent_id = Column(
        UUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    task_type = Column(String(100), nullable=False)
    risk_classification = Column(String(50), default="low", nullable=False)
    state = Column(
        String(50), default="queued", nullable=False
    )  # queued, running, blocked, completed, failed, cancelled
    idempotency_key = Column(String(255), nullable=True, index=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    retry_count = Column(Integer, default=0, nullable=False)
    error_message = Column(Text, nullable=True)

    tenant = relationship("Tenant")
    agent = relationship("Agent")


class Approval(Base, TimestampMixin):
    """Approval records for consequential actions."""

    __tablename__ = "approvals"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    requested_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    approved_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    state = Column(
        String(50), default="pending", nullable=False
    )  # pending, granted, denied, expired
    expires_at = Column(DateTime(timezone=True), nullable=True)


class AuditEvent(Base, TimestampMixin):
    """Tamper-evident audit records."""

    __tablename__ = "audit_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    actor_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    event_type = Column(String(100), nullable=False, index=True)
    event_category = Column(
        String(50), nullable=False
    )  # security, auth, system, tool, agent, memory
    outcome = Column(String(50), nullable=False)  # success, failure, denial
    details = Column(Text, nullable=True)
    occurred_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
