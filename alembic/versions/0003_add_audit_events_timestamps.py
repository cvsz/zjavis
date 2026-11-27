"""Add created_at and updated_at to audit_events.

The AuditEvent model extends TimestampMixin, which requires created_at and
updated_at columns, but the initial schema (0001_initial_schema.py) omitted
them from the audit_events table. This migration adds the missing columns so
the database schema matches the SQLAlchemy model metadata.

Revision ID: 0003_add_audit_events_timestamps
Revises: 0002_add_role_permissions
Create Date: 2026-11-28
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0003_add_audit_events_timestamps"
down_revision = "0002_add_role_permissions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add created_at and updated_at columns to audit_events."""
    op.add_column(
        "audit_events",
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.add_column(
        "audit_events",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    """Remove created_at and updated_at columns from audit_events."""
    op.drop_column("audit_events", "updated_at")
    op.drop_column("audit_events", "created_at")
