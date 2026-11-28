"""Unit tests for the JARVIS memory service."""

from __future__ import annotations

import math
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from jarvis.ai.memory import (
    MemoryService,
    chunk_text,
    deserialize_embedding,
    generate_content_hash,
    serialize_embedding,
)
from jarvis.db.models import Memory


def _scalar_mock(value: Any) -> MagicMock:
    """Create a MagicMock whose scalar_one_or_none returns the given value."""
    mock = MagicMock()
    mock.scalar_one_or_none = lambda: value
    return mock


def _scalars_mock(values: list[Any]) -> MagicMock:
    """Create a MagicMock whose scalars().all() returns the given list."""
    mock = MagicMock()
    mock.scalars = lambda: MagicMock(all=lambda: values)
    return mock


class TestGenerateContentHash:
    """Tests for content hash generation."""

    def test_generate_content_hash_deterministic(self) -> None:
        h1 = generate_content_hash("hello world")
        h2 = generate_content_hash("hello world")
        assert h1 == h2
        assert len(h1) == 64  # SHA-256 hex

    def test_generate_content_hash_different(self) -> None:
        assert generate_content_hash("a") != generate_content_hash("b")


class TestChunkText:
    """Tests for text chunking."""

    def test_chunk_text_short(self) -> None:
        result = chunk_text("hello", chunk_size=100, overlap=10)
        assert result == ["hello"]

    def test_chunk_text_exact(self) -> None:
        result = chunk_text("hello world", chunk_size=11, overlap=0)
        assert result == ["hello world"]

    def test_chunk_text_long(self) -> None:
        text = "a" * 2500
        result = chunk_text(text, chunk_size=1000, overlap=200)
        assert len(result) > 1
        assert len(result[0]) == 1000

    def test_chunk_text_empty(self) -> None:
        result = chunk_text("", chunk_size=100, overlap=10)
        assert result == [""]


class TestMemoryService:
    """Tests for MemoryService."""

    @pytest.fixture
    def mock_session(self) -> AsyncSession:
        session = AsyncMock(spec=AsyncSession)
        return session

    @pytest.mark.asyncio
    async def test_add_memory(self, mock_session: AsyncSession) -> None:
        service = MemoryService(mock_session)
        mock_session.execute.return_value = _scalar_mock(None)  # type: ignore[attr-defined]

        memory = await service.add_memory(
            tenant_id="tenant-1",
            user_id="user-1",
            memory_type="conversation",
            content="test content",
        )
        assert memory.content == "test content"
        assert memory.memory_type == "conversation"
        mock_session.add.assert_called_once()  # type: ignore[attr-defined]
        mock_session.commit.assert_called()  # type: ignore[attr-defined]

    @pytest.mark.asyncio
    async def test_add_memory_duplicate(self, mock_session: AsyncSession) -> None:
        from jarvis.db.models import Memory

        service = MemoryService(mock_session)
        existing = Memory(
            id="existing-id",
            tenant_id="tenant-1",
            user_id="user-1",
            memory_type="conversation",
            content="test content",
        )
        mock_session.execute.return_value = _scalar_mock(existing)  # type: ignore[attr-defined]

        memory = await service.add_memory(
            tenant_id="tenant-1",
            user_id="user-1",
            memory_type="conversation",
            content="test content",
        )
        assert memory.id == "existing-id"

    @pytest.mark.asyncio
    async def test_get_memory(self, mock_session: AsyncSession) -> None:
        from jarvis.db.models import Memory

        service = MemoryService(mock_session)
        expected = Memory(
            id="mem-1",
            tenant_id="tenant-1",
            user_id="user-1",
            memory_type="conversation",
            content="test",
        )
        mock_session.execute.return_value = _scalar_mock(expected)  # type: ignore[attr-defined]

        memory = await service.get_memory("mem-1", "tenant-1")
        assert memory == expected

    @pytest.mark.asyncio
    async def test_get_memory_not_found(self, mock_session: AsyncSession) -> None:
        service = MemoryService(mock_session)
        mock_session.execute.return_value = _scalar_mock(None)  # type: ignore[attr-defined]

        memory = await service.get_memory("nonexistent", "tenant-1")
        assert memory is None

    @pytest.mark.asyncio
    async def test_search_memories(self, mock_session: AsyncSession) -> None:
        from jarvis.db.models import Memory

        service = MemoryService(mock_session)
        m1 = Memory(
            id="m1", tenant_id="t1", user_id="u1", memory_type="c", content="hello"
        )
        m2 = Memory(
            id="m2", tenant_id="t1", user_id="u1", memory_type="c", content="world"
        )
        mock_session.execute.return_value = _scalars_mock([m1, m2])  # type: ignore[attr-defined]

        memories = await service.search_memories(tenant_id="t1", query="hello")
        assert len(memories) == 2

    @pytest.mark.asyncio
    async def test_delete_memory(self, mock_session: AsyncSession) -> None:
        from jarvis.db.models import Memory

        service = MemoryService(mock_session)
        memory = Memory(
            id="m1", tenant_id="t1", user_id="u1", memory_type="c", content="test"
        )
        mock_session.execute.return_value = _scalar_mock(memory)  # type: ignore[attr-defined]

        result = await service.delete_memory("m1", "t1")
        assert result is True
        assert memory.is_deleted is True

    @pytest.mark.asyncio
    async def test_delete_memory_not_found(self, mock_session: AsyncSession) -> None:
        service = MemoryService(mock_session)
        mock_session.execute.return_value = _scalar_mock(None)  # type: ignore[attr-defined]

        result = await service.delete_memory("nonexistent", "t1")
        assert result is False

    @pytest.mark.asyncio
    async def test_delete_expired_memories(self, mock_session: AsyncSession) -> None:
        from datetime import UTC, datetime

        from jarvis.db.models import Memory

        service = MemoryService(mock_session)
        expired = Memory(
            id="exp1",
            tenant_id="t1",
            user_id="u1",
            memory_type="c",
            content="old",
            expires_at=datetime.now(UTC),
        )
        mock_session.execute.return_value = _scalars_mock([expired])  # type: ignore[attr-defined]

        count = await service.delete_expired_memories()
        assert count == 1
        assert expired.is_deleted is True

    @pytest.mark.asyncio
    async def test_get_memory_stats(self, mock_session: AsyncSession) -> None:
        from jarvis.db.models import Memory

        service = MemoryService(mock_session)
        m1 = Memory(
            id="m1",
            tenant_id="t1",
            user_id="u1",
            memory_type="conversation",
            content="a",
        )
        m2 = Memory(
            id="m2", tenant_id="t1", user_id="u1", memory_type="episodic", content="b"
        )
        mock_session.execute.return_value = _scalars_mock([m1, m2])  # type: ignore[attr-defined]

        stats = await service.get_memory_stats("t1")
        assert stats["total"] == 2
        assert stats["by_type"]["conversation"] == 1
        assert stats["by_type"]["episodic"] == 1


class TestLocalEmbeddingFunction:
    """Tests for the deterministic local embedding function."""

    def test_embed_is_deterministic(self) -> None:
        from jarvis.ai.memory import LocalEmbeddingFunction

        fn = LocalEmbeddingFunction(dimension=128)
        v1 = fn.embed(["hello world"])
        v2 = fn.embed(["hello world"])
        assert v1 == v2

    def test_embed_unit_normalized(self) -> None:
        from jarvis.ai.memory import LocalEmbeddingFunction

        fn = LocalEmbeddingFunction(dimension=128)
        vector = fn.embed(["hello world"])[0]
        norm = math.sqrt(sum(v * v for v in vector))
        assert abs(norm - 1.0) < 1e-6

    def test_embed_similar_texts_score_higher(self) -> None:
        from jarvis.ai.memory import LocalEmbeddingFunction, cosine_similarity

        fn = LocalEmbeddingFunction(dimension=256)
        v_shared = fn.embed(["the quick brown fox"])[0]
        v_same_words = fn.embed(["the quick brown fox jumps"])[0]
        v_unrelated = fn.embed(["completely unrelated topic here"])[0]
        assert cosine_similarity(v_shared, v_same_words) > cosine_similarity(
            v_shared, v_unrelated
        )

    def test_embed_empty_text(self) -> None:
        from jarvis.ai.memory import LocalEmbeddingFunction

        fn = LocalEmbeddingFunction(dimension=64)
        vector = fn.embed([""])[0]
        assert all(v == 0.0 for v in vector)


class TestEmbeddingSerialization:
    """Tests for embedding serialize/deserialize helpers."""

    def test_serialize_roundtrip(self) -> None:
        from jarvis.ai.memory import deserialize_embedding, serialize_embedding

        vector = [0.1, -0.2, 0.3]
        assert deserialize_embedding(serialize_embedding(vector)) == vector

    def test_deserialize_none(self) -> None:
        from jarvis.ai.memory import deserialize_embedding

        assert deserialize_embedding(None) is None

    def test_deserialize_invalid(self) -> None:
        from jarvis.ai.memory import deserialize_embedding

        assert deserialize_embedding("not json") is None


class TestCosineSimilarity:
    """Tests for cosine similarity."""

    def test_identical_vectors(self) -> None:
        from jarvis.ai.memory import cosine_similarity

        assert cosine_similarity([1.0, 0.0], [1.0, 0.0]) == 1.0

    def test_orthogonal_vectors(self) -> None:
        from jarvis.ai.memory import cosine_similarity

        assert cosine_similarity([1.0, 0.0], [0.0, 1.0]) == 0.0

    def test_opposite_vectors(self) -> None:
        from jarvis.ai.memory import cosine_similarity

        assert cosine_similarity([1.0, 0.0], [-1.0, 0.0]) == -1.0

    def test_empty(self) -> None:
        from jarvis.ai.memory import cosine_similarity

        assert cosine_similarity([], []) == 0.0


class TestSemanticSearch:
    """Tests for semantic memory search (tenant-isolated, threshold-filtered)."""

    @pytest.fixture
    def mock_session(self) -> AsyncSession:
        session = AsyncMock(spec=AsyncSession)
        return session

    def _memory_with_embedding(
        self,
        memory_id: str,
        tenant_id: str,
        content: str,
        vector: list[float],
        memory_type: str = "semantic",
    ) -> Memory:
        memory = Memory(
            id=memory_id,
            tenant_id=tenant_id,
            user_id="u1",
            memory_type=memory_type,
            content=content,
        )
        memory.embedding = serialize_embedding(vector)
        return memory

    @pytest.mark.asyncio
    async def test_semantic_search_returns_best_match_first(
        self, mock_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        service = MemoryService(mock_session)
        # Fixed query vector: [1.0, 0.0]. m1 aligns with it; m2 is orthogonal.
        monkeypatch.setattr(
            service.embedding_function,
            "embed",
            lambda texts: [[1.0, 0.0]] * len(texts),
        )

        m_similar = self._memory_with_embedding("m1", "t1", "x", [1.0, 0.0])
        m_unrelated = self._memory_with_embedding("m2", "t1", "y", [0.0, 1.0])
        # Other tenant: must not be returned.
        m_other = self._memory_with_embedding("m3", "t2", "x", [1.0, 0.0])
        mock_session.execute.return_value = _scalars_mock(
            [m_similar, m_unrelated, m_other]
        )

        results = await service.search_memories_semantic(
            tenant_id="t1", query="anything", limit=5
        )
        ids = [str(m.id) for m, _ in results]
        assert ids == ["m1", "m2"]
        assert "m3" not in ids  # tenant isolation
        # Best match (similar) comes first and has higher similarity.
        assert results[0][0].id == m_similar.id
        assert results[0][1] > results[1][1]

    @pytest.mark.asyncio
    async def test_semantic_search_filters_by_threshold(
        self, mock_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        service = MemoryService(mock_session)
        monkeypatch.setattr(
            service.embedding_function,
            "embed",
            lambda texts: [[1.0, 0.0]] * len(texts),
        )

        m_similar = self._memory_with_embedding("m1", "t1", "x", [1.0, 0.0])
        m_unrelated = self._memory_with_embedding("m2", "t1", "y", [0.0, 1.0])
        mock_session.execute.return_value = _scalars_mock([m_similar, m_unrelated])

        results = await service.search_memories_semantic(
            tenant_id="t1",
            query="anything",
            limit=5,
            threshold=0.5,
        )
        # Only the aligned vector meets the 0.5 threshold.
        assert len(results) == 1
        assert results[0][0].id == m_similar.id

    @pytest.mark.asyncio
    async def test_semantic_search_filters_by_memory_type(
        self, mock_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        service = MemoryService(mock_session)
        monkeypatch.setattr(
            service.embedding_function,
            "embed",
            lambda texts: [[1.0, 0.0]] * len(texts),
        )

        vector = [1.0, 0.0]
        m_semantic = self._memory_with_embedding(
            "m1", "t1", "x", vector, memory_type="semantic"
        )
        m_conversation = self._memory_with_embedding(
            "m2", "t1", "x", vector, memory_type="conversation"
        )
        mock_session.execute.return_value = _scalars_mock([m_semantic, m_conversation])

        results = await service.search_memories_semantic(
            tenant_id="t1",
            query="anything",
            memory_type="semantic",
            limit=5,
        )
        assert len(results) == 1
        assert results[0][0].memory_type == "semantic"

    @pytest.mark.asyncio
    async def test_semantic_search_skips_memories_without_embedding(
        self, mock_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        service = MemoryService(mock_session)
        monkeypatch.setattr(
            service.embedding_function,
            "embed",
            lambda texts: [[1.0, 0.0]] * len(texts),
        )

        m_with = self._memory_with_embedding("m1", "t1", "alpha", [1.0, 0.0])
        m_without = Memory(
            id="m2",
            tenant_id="t1",
            user_id="u1",
            memory_type="semantic",
            content="beta",
        )
        m_without.embedding = None
        mock_session.execute.return_value = _scalars_mock([m_with, m_without])

        results = await service.search_memories_semantic(
            tenant_id="t1", query="alpha", limit=5
        )
        assert len(results) == 1
        assert results[0][0].id == m_with.id

    @pytest.mark.asyncio
    async def test_semantic_search_empty_query(
        self, mock_session: AsyncSession
    ) -> None:
        service = MemoryService(mock_session)
        results = await service.search_memories_semantic(
            tenant_id="t1", query="   ", limit=5
        )
        assert results == []


class TestIngestText:
    """Tests for document/text ingestion into memory."""

    @pytest.fixture
    def mock_session(self) -> AsyncSession:
        session = AsyncMock(spec=AsyncSession)
        # No duplicates: add_memory's duplicate check returns None.
        session.execute.return_value = _scalar_mock(None)
        return session

    @pytest.mark.asyncio
    async def test_ingest_text_creates_chunked_memories(
        self, mock_session: AsyncSession
    ) -> None:
        service = MemoryService(mock_session)
        # 2400 chars -> 3 chunks of 1000 with 200 overlap.
        content = "x " * 1200
        created = await service.ingest_text(
            tenant_id="t1", user_id="u1", content=content, source="s1"
        )
        assert len(created) > 1
        # Every created memory has an embedding and the document source.
        for m in created:
            assert deserialize_embedding(m.embedding) is not None
            assert m.source == "s1"
            assert m.source_type == "text"
            assert m.memory_type == "semantic"
        # Called once per chunk.
        assert mock_session.add.call_count == len(created)


class TestIngestDocument:
    """Tests for the document ingestion convenience wrapper."""

    @pytest.fixture
    def mock_session(self) -> AsyncSession:
        session = AsyncMock(spec=AsyncSession)
        session.execute.return_value = _scalar_mock(None)
        return session

    @pytest.mark.asyncio
    async def test_ingest_document_defaults_source_type_to_document(
        self, mock_session: AsyncSession
    ) -> None:
        service = MemoryService(mock_session)
        created = await service.ingest_document(
            tenant_id="t1",
            user_id="u1",
            content="document content here",
            source="doc-1",
        )
        assert len(created) == 1
        assert created[0].source == "doc-1"
        assert created[0].source_type == "document"
