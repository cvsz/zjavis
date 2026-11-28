"""Add embedding column to memories for semantic retrieval.

Revision ID: 0004_add_memory_embedding
Revises: 0003_add_audit_events_timestamps
Create Date: 2026-11-28

Adds a nullable ``embedding`` column to the ``memories`` table. Embeddings are
stored as JSON-encoded float lists so semantic/vector retrieval works without
requiring the pgvector PostgreSQL extension. When pgvector is available, the
column can be migrated to a native ``vector`` type for SQL-level similarity
search without changing the application interface.

Per javis-blueprint.md section 7.4, semantic retrieval is part of the memory
lifecycle; this column stores the per-chunk embedding produced by the local
embedding function so that ``MemoryService.search_memories_semantic()`` can
rank results by cosine similarity.
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0004_add_memory_embedding"
down_revision = "0003_add_audit_events_timestamps"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add the embedding column to the memories table."""
    op.add_column(
        "memories",
        sa.Column(
            "embedding",
            sa.Text(),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_memories_embedding", "memories", ["embedding"], unique=False
    )


def downgrade() -> None:
    """Remove the embedding column from the memories table."""
    op.drop_index("ix_memories_embedding", table_name="memories")
    op.drop_column("memories", "embedding")
