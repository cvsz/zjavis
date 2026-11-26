"""Database dependency provider for FastAPI routes.

Re-exports the session dependency so route modules can import from a
single location.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from jarvis.db.session import async_session, get_session

__all__ = ["AsyncSession", "async_session", "get_session"]
