"""Unit tests for the JARVIS memory service."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from jarvis.ai.memory import MemoryService, chunk_text, generate_content_hash


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
