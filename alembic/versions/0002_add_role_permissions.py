"""Add role_permissions junction table.

Revision ID: 0002_add_role_permissions
Revises: 0001_initial_schema
Create Date: 2026-11-27

Creates the many-to-many association between roles and permissions so that
roles can carry atomic permissions. This fixes the broken RBAC resolution in
``jarvis.auth.get_user_permissions()`` which previously joined
``role_bindings.role_id`` directly against ``permissions.id`` (two unrelated
tables) and therefore resolved to an empty permission set for every user.

Per javis-blueprint.md section 13.1, roles define named permission sets; this
table is the association mechanism that was missing from the initial schema.
"""

from __future__ import annotations

import uuid

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0002_add_role_permissions"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create the role_permissions association table."""
    op.create_table(
        "role_permissions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            default=uuid.uuid4,
        ),
        sa.Column(
            "role_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("roles.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "permission_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("permissions.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            onupdate=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "role_id", "permission_id", name="uq_role_permission"
        ),
    )


def downgrade() -> None:
    """Drop the role_permissions association table."""
    op.drop_table("role_permissions")
