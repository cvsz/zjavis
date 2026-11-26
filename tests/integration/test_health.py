"""Integration tests for health endpoints.

Tests the /health (liveness) and /ready (readiness) endpoints against
the real FastAPI application with a live database.
"""

from __future__ import annotations

import anyio
from httpx import ASGITransport, AsyncClient


async def _run_health(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "alive"
        assert data["service"] == "jarvis"


async def _run_ready(app):
    from jarvis.db.session import init_db

    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
        assert data["service"] == "jarvis"
        assert "checks" in data
        assert data["checks"]["database"]["status"] == "up"


def test_health_endpoint(app) -> None:
    """Liveness probe returns alive status."""
    anyio.run(_run_health, app)


def test_ready_endpoint(app) -> None:
    """Readiness probe returns ready when database is reachable."""
    anyio.run(_run_ready, app)
