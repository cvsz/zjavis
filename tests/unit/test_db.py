"""Unit tests for the JARVIS database session module."""

from __future__ import annotations

# Import models to populate Base.metadata with table definitions.
from jarvis.db.models import (  # noqa: F401
    Agent,
    Approval,
    AuditEvent,
    Conversation,
    Memory,
    Message,
    Organization,
    Permission,
    Role,
    RoleBinding,
    Task,
    Tenant,
    User,
)
from jarvis.db.session import Base


def test_base_metadata_has_tables() -> None:
    """The declarative base has registered table metadata."""
    table_names = list(Base.metadata.tables.keys())
    expected = {
        "organizations",
        "users",
        "tenants",
        "roles",
        "permissions",
        "role_bindings",
        "sessions",
        "conversations",
        "messages",
        "memories",
        "agents",
        "tasks",
        "approvals",
        "audit_events",
    }
    for expected_table in expected:
        assert expected_table in table_names, f"Missing table: {expected_table}"
