"""Memory and knowledge intelligence system.

Provides memory management, document ingestion, chunking, hybrid retrieval,
tenant-aware access filters, retention, and deletion capabilities.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from datetime import UTC, datetime
from typing import Any, Protocol

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from jarvis.core.logging import get_logger
from jarvis.db.models import Memory

logger = get_logger(__name__)

_TOKEN_SPLIT = re.compile(r"[^a-z0-9]+")


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


def _tokenize(text: str) -> list[str]:
    """Split text into lowercase alphanumeric tokens."""
    return [t for t in _TOKEN_SPLIT.split(text.lower()) if t]


def _token_hash(token: str, dimension: int) -> tuple[int, int]:
    """Deterministically map a token to a signed vector index.

    Uses SHA-256 (not Python's randomized ``hash()``) so embeddings are
    identical across processes and restarts. The first hash word selects the
    vector dimension; the second selects the sign. This is the feature-hashing
    trick: texts sharing tokens produce similar vectors.
    """
    digest = hashlib.sha256(token.encode("utf-8")).digest()
    index = int.from_bytes(digest[:4], "little") % dimension
    sign = 1 if int.from_bytes(digest[4:8], "little") % 2 == 0 else -1
    return index, sign


def serialize_embedding(vector: list[float]) -> str:
    """Serialize an embedding vector to a JSON string for storage."""
    return json.dumps(vector)


def deserialize_embedding(value: str | None) -> list[float] | None:
    """Deserialize a stored embedding, or return None if absent/invalid."""
    if value is None:
        return None
    try:
        return [float(x) for x in json.loads(value)]
    except (json.JSONDecodeError, TypeError, ValueError):
        return None


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Cosine similarity between two vectors (assumes caller normalizes)."""
    if len(a) != len(b) or not a:
        return 0.0
    dot = 0.0
    norm_a = 0.0
    norm_b = 0.0
    for x, y in zip(a, b):
        dot += x * y
        norm_a += x * x
        norm_b += y * y
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (math.sqrt(norm_a) * math.sqrt(norm_b))


class EmbeddingFunction(Protocol):
    """Protocol for embedding functions that turn text into vectors.

    Implementations may call external model providers (requiring credentials)
    or run fully locally. The memory service does not embed provider logic.
    """

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed a list of texts, returning one vector per text."""


class LocalEmbeddingFunction:
    """Deterministic local embedding function requiring no credentials.

    Uses the feature-hashing trick over a fixed-dimensional vector. Suitable
    for semantic retrieval in air-gapped or credential-free environments and
    for tests. Not a substitute for a trained model; replace with a real
    embedding provider when one is available.
    """

    def __init__(self, *, dimension: int = 256) -> None:
        self.dimension = dimension

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed a list of texts, returning one unit-normalized vector each."""
        return [self._embed_one(text) for text in texts]

    def _embed_one(self, text: str) -> list[float]:
        vector = [0.0] * self.dimension
        for token in _tokenize(text):
            index, sign = _token_hash(token, self.dimension)
            vector[index] += float(sign)
        norm = math.sqrt(sum(v * v for v in vector))
        if norm > 0.0:
            vector = [v / norm for v in vector]
        return vector


class MemoryService:
    """Memory service for managing memory items with tenant isolation,
    source provenance, retention, and hybrid retrieval."""

    def __init__(
        self,
        session: AsyncSession,
        embedding_function: EmbeddingFunction | None = None,
    ) -> None:
        self.session = session
        self.embedding_function = embedding_function or LocalEmbeddingFunction()

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
        embedding: list[float] | None = None,
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
            embedding: Optional pre-computed embedding vector. When omitted,
                the service's embedding function derives one from ``content``.

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

        if embedding is None and content.strip():
            embedding = self.embedding_function.embed([content])[0]

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
            embedding=serialize_embedding(embedding) if embedding else None,
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

    async def search_memories_semantic(
        self,
        *,
        tenant_id: str,
        query: str,
        memory_type: str | None = None,
        limit: int = 10,
        threshold: float = 0.0,
    ) -> list[tuple[Memory, float]]:
        """Semantic (vector-similarity) search over memories with tenant isolation.

        Embeds the query, computes cosine similarity against every non-deleted
        memory for the tenant that has an embedding, and returns the top
        matches above ``threshold``. This works without the pgvector PostgreSQL
        extension because embeddings are stored as JSON and compared in Python;
        when pgvector is available this can be promoted to a SQL query without
        changing the interface.

        Args:
            tenant_id: Tenant ID for isolation.
            query: Search query text.
            memory_type: Optional memory type filter.
            limit: Maximum number of results.
            threshold: Minimum cosine similarity (0.0-1.0) to include.

        Returns:
            List of ``(Memory, similarity)`` tuples, best match first.
        """
        if not query.strip():
            return []

        query_stmt = select(Memory).where(
            Memory.tenant_id == tenant_id,
            Memory.is_deleted == False,
            Memory.embedding.is_not(None),
        )
        if memory_type:
            query_stmt = query_stmt.where(Memory.memory_type == memory_type)

        result = await self.session.execute(query_stmt)
        memories = result.scalars().all()

        query_vector = self.embedding_function.embed([query])[0]
        scored: list[tuple[Memory, float]] = []
        for memory in memories:
            # Defensive Python-side filters (the SQL query also applies them,
            # but this keeps behavior correct when the session is mocked).
            if str(memory.tenant_id) != str(tenant_id):
                continue
            if memory_type is not None and str(memory.memory_type) != memory_type:
                continue
            if memory.is_deleted:
                continue
            vector = deserialize_embedding(memory.embedding)
            if vector is None:
                continue
            similarity = cosine_similarity(query_vector, vector)
            if similarity >= threshold:
                scored.append((memory, similarity))

        scored.sort(key=lambda pair: pair[1], reverse=True)
        return scored[:limit]

    async def ingest_text(
        self,
        *,
        tenant_id: str,
        user_id: str,
        content: str,
        source: str | None = None,
        source_type: str | None = "text",
        source_id: str | None = None,
        memory_type: str = "semantic",
        confidence: int | None = 80,
        chunk_size: int = 1000,
        overlap: int = 200,
    ) -> list[Memory]:
        """Ingest free text into memory: chunk, embed, and store each chunk.

        Each chunk becomes a separate ``semantic``-typed memory item with its
        own embedding, enabling retrieval of the most relevant chunks later.

        Args:
            tenant_id: Tenant ID for isolation.
            user_id: User ID who owns the memory.
            content: Text to ingest.
            source: Human-readable source identifier.
            source_type: Type of source (default ``"text"``).
            source_id: External source identifier.
            memory_type: Memory type for the created items.
            confidence: Confidence score 0-100.
            chunk_size: Maximum characters per chunk.
            overlap: Overlap between adjacent chunks.

        Returns:
            List of created (or existing duplicate) Memory objects.
        """
        chunks = chunk_text(content, chunk_size=chunk_size, overlap=overlap)
        if not chunks:
            return []

        texts = list(chunks)
        vectors = self.embedding_function.embed(texts)

        created: list[Memory] = []
        for chunk, vector in zip(texts, vectors):
            memory = await self.add_memory(
                tenant_id=tenant_id,
                user_id=user_id,
                memory_type=memory_type,
                content=chunk,
                source=source,
                source_type=source_type,
                source_id=source_id,
                confidence=confidence,
                embedding=vector,
            )
            created.append(memory)
        return created

    async def ingest_document(
        self,
        *,
        tenant_id: str,
        user_id: str,
        content: str,
        source: str,
        source_type: str = "document",
        source_id: str | None = None,
        memory_type: str = "semantic",
        confidence: int | None = 80,
        chunk_size: int = 1000,
        overlap: int = 200,
    ) -> list[Memory]:
        """Ingest a document into memory.

        Convenience wrapper around :meth:`ingest_text` with source defaulting
        to ``"document"``. See :meth:`ingest_text` for argument details.

        Returns:
            List of created (or existing duplicate) Memory objects.
        """
        return await self.ingest_text(
            tenant_id=tenant_id,
            user_id=user_id,
            content=content,
            source=source,
            source_type=source_type,
            source_id=source_id,
            memory_type=memory_type,
            confidence=confidence,
            chunk_size=chunk_size,
            overlap=overlap,
        )
