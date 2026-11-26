"""Database session and connection management.

Provides a SQLAlchemy async engine, session factory, and dependency
for FastAPI route handlers. Connection parameters are read exclusively
from environment configuration (never hardcoded).
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from jarvis.core.config import settings
from jarvis.core.logging import get_logger

logger = get_logger(__name__)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy declarative models."""


# Create the async engine from the configured DATABASE_URL.
# pool_pre_ping helps recover from stale connections.
engine = create_async_engine(
    settings.database_url,
    echo=settings.database_echo,
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
    pool_pre_ping=True,
)

# Session factory bound to the engine.
async_session = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields a database session.

    Yields:
        An :class:`AsyncSession` that is automatically closed after use.

    Example:
        @app.get("/")
        async def index(session: AsyncSession = Depends(get_session)):
            ...
    """
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db() -> None:
    """Initialize the database by creating all tables.

    Intended for development and test bootstrap. Production schema
    changes must go through Alembic migrations.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created")
