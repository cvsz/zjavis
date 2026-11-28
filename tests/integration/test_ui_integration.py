"""Integration tests for the Phase 10 web UI and model status routes.

Drives the real FastAPI application through ASGITransport. Page routes
(/login, /dashboard) return HTML without authentication; the /api/v1/models
endpoints require a bearer token (401 when unauthenticated).
"""

from __future__ import annotations

import anyio
from httpx import ASGITransport, AsyncClient

from jarvis.api.main import create_app


async def _get(client: AsyncClient, path: str):
    return await client.get(path)


def test_login_page_returns_html() -> None:
    app = create_app()

    async def run() -> None:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            response = await _get(ac, "/login")
            assert response.status_code == 200
            assert "text/html" in response.headers.get("content-type", "")
            assert "JARVIS" in response.text
            assert 'id="loginForm"' in response.text

    anyio.run(run)


def test_dashboard_page_returns_html() -> None:
    app = create_app()

    async def run() -> None:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            response = await _get(ac, "/dashboard")
            assert response.status_code == 200
            assert "text/html" in response.headers.get("content-type", "")
            assert "System Health" in response.text
            assert "Model Status" in response.text

    anyio.run(run)


def test_root_redirects_to_dashboard() -> None:
    app = create_app()

    async def run() -> None:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            response = await _get(ac, "/")
            assert response.status_code == 302
            assert response.headers["location"] == "/dashboard"

    anyio.run(run)


def test_models_endpoint_requires_auth() -> None:
    app = create_app()

    async def run() -> None:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            response = await _get(ac, "/api/v1/models")
            assert response.status_code == 401

    anyio.run(run)
