"""Memory and knowledge intelligence system.

Provides memory management, document ingestion, chunking, hybrid retrieval,
tenant-aware access filters, retention, and deletion capabilities.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from jarvis.core.logging import get_logger
from jarvis.db.models import Memory

logger = get_logger(__name__)


def generate_content_hash(content: str) -> str:
    """Generate SHA-256 hash of content for deduplication."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def chunk_text(
    text: str,
    chunk_size: int = 1000,
    overlap: int = 200,
) -> list[str]:
    """Split text into overlapping chunks.

    Args:
        text: Text to chunk.
        chunk_size: Maximum characters per chunk.
        overlap: Number of characters to overlap between chunks.

    Returns:
        List of text chunks.
    """
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        start = end - overlap
        if start >= len(text):
            break

    return chunks


class MemoryService:
    """Memory service for managing memory items with tenant isolation,
    source provenance, retention, and hybrid retrieval."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add_memory(
        self,
        *,
        tenant_id: str,
        user_id: str,
        memory_type: str,
        content: str,
        source: str | None = None,
        source_type: str | None = None,
        source_id: str | None = None,
        confidence: int | None = None,
        expires_at: str | None = None,
    ) -> Memory:
        """Create a memory item with provenance tracking.

        Args:
            tenant_id: Tenant ID for isolation.
            user_id: User ID who owns the memory.
            memory_type: Type of memory (working, conversation, episodic,
                semantic, procedural, project, preference).
            content: Memory content.
            source: Source identifier (human-readable).
            source_type: Type of source (document, web, conversation, etc.).
            source_id: External source identifier.
            confidence: Confidence score 0-100.
            expires_at: Optional expiration timestamp.

        Returns:
            Created Memory object.
        """
        content_hash = generate_content_hash(content)

        # Check for duplicate content
        existing = await self.session.execute(
            select(Memory).where(
                Memory.content_hash == content_hash,
                Memory.tenant_id == tenant_id,
                Memory.is_deleted == False,
            )
        )
        existing_memory = existing.scalar_one_or_none()
        if existing_memory:
            logger.info(
                "Duplicate memory detected, returning existing",
                extra={
                    "memory_id": str(existing_memory.id),
                    "content_hash": content_hash,
                },
            )
            return existing_memory

        memory = Memory(
            tenant_id=tenant_id,
            user_id=user_id,
            memory_type=memory_type,
            content=content,
            content_hash=content_hash,
            source=source,
            source_type=source_type,
            source_id=source_id,
            confidence=confidence,
            expires_at=expires_at,
        )
        self.session.add(memory)
        await self.session.commit()
        await self.session.refresh(memory)

        logger.info(
            "Memory created",
            extra={
                "memory_id": str(memory.id),
                "tenant_id": str(tenant_id),
                "memory_type": memory_type,
                "content_hash": content_hash,
            },
        )
        return memory

    async def get_memory(
        self,
        memory_id: str,
        tenant_id: str,
    ) -> Memory | None:
        """Retrieve a memory by ID with tenant isolation.

        Args:
            memory_id: Memory ID.
            tenant_id: Tenant ID for isolation.

        Returns:
            Memory object or None if not found.
        """
        result = await self.session.execute(
            select(Memory).where(
                Memory.id == memory_id,
                Memory.tenant_id == tenant_id,
                Memory.is_deleted == False,
            )
        )
        return result.scalar_one_or_none()

    async def search_memories(
        self,
        *,
        tenant_id: str,
        query: str | None = None,
        memory_type: str | None = None,
        limit: int = 10,
    ) -> list[Memory]:
        """Search memories with tenant isolation and optional keyword filter.

        Args:
            tenant_id: Tenant ID for isolation.
            query: Optional search query for keyword matching.
            memory_type: Optional memory type filter.
            limit: Maximum number of results.

        Returns:
            List of matching Memory objects.
        """
        query_stmt = select(Memory).where(
            Memory.tenant_id == tenant_id,
            Memory.is_deleted == False,
        )

        if memory_type:
            query_stmt = query_stmt.where(Memory.memory_type == memory_type)

        if query:
            search_term = f"%{query.lower()}%"
            query_stmt = query_stmt.where(Memory.content.ilike(search_term))

        query_stmt = query_stmt.order_by(Memory.created_at.desc()).limit(limit)
        result = await self.session.execute(query_stmt)
        return list(result.scalars().all())

    async def delete_memory(
        self,
        memory_id: str,
        tenant_id: str,
    ) -> bool:
        """Soft-delete a memory item with tenant isolation.

        Args:
            memory_id: Memory ID.
            tenant_id: Tenant ID for isolation.

        Returns:
            True if memory was found and deleted, False otherwise.
        """
        memory = await self.get_memory(memory_id, tenant_id)
        if memory is None:
            return False

        memory.is_deleted = True
        await self.session.commit()
        logger.info(
            "Memory deleted",
            extra={"memory_id": str(memory_id), "tenant_id": str(tenant_id)},
        )
        return True

    async def delete_expired_memories(self) -> int:
        """Delete expired memories across all tenants.

        Returns:
            Number of memories deleted.
        """
        now = datetime.now(UTC)
        result = await self.session.execute(
            select(Memory).where(
                Memory.is_deleted.is_(False),
                Memory.expires_at < now,
            )
        )
        expired_memories = result.scalars().all()
        count = len(expired_memories)
        for memory in expired_memories:
            memory.is_deleted = True
        await self.session.commit()
        logger.info("Expired memories deleted", extra={"count": count})
        return count

    async def get_memory_stats(self, tenant_id: str) -> dict[str, Any]:
        """Get memory statistics for a tenant.

        Args:
            tenant_id: Tenant ID for isolation.

        Returns:
            Dict with memory statistics.
        """
        result = await self.session.execute(
            select(Memory).where(
                Memory.tenant_id == tenant_id,
                Memory.is_deleted == False,
            )
        )
        memories = result.scalars().all()

        type_counts: dict[str, int] = {}
        for m in memories:
            type_counts[str(m.memory_type)] = type_counts.get(str(m.memory_type), 0) + 1

        return {
            "total": len(memories),
            "by_type": type_counts,
            "tenant_id": str(tenant_id),
        }
