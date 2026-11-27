"""Integration tests for authentication endpoints.

Tests login, token retrieval, and current-user endpoints against the
real application with a live database.
"""

from __future__ import annotations

import uuid

import anyio
from httpx import ASGITransport, AsyncClient

from jarvis.core.security import hash_password
from jarvis.db.models import Organization, Tenant, User


async def _create_user_and_login(
    app, username, email, password, login_password, org_name=None, org_slug=None
):
    from jarvis.db.session import async_session, init_db

    await init_db()
    # Use unique identifiers to avoid conflicts with prior test data
    unique = uuid.uuid4().hex[:8]
    if org_name is None:
        org_name = f"Test Org {unique}"
    if org_slug is None:
        org_slug = f"test-org-{unique}"
    if username is None:
        username = f"testuser_{unique}"

    async with async_session() as db_session:
        org = Organization(name=org_name, slug=org_slug)
        db_session.add(org)
        await db_session.flush()
        tenant = Tenant(
            organization_id=org.id,
            name=org_name,
            slug=org_slug,
        )
        db_session.add(tenant)
        await db_session.flush()
        user = User(
            organization_id=org.id,
            tenant_id=tenant.id,
            email=email,
            username=username,
            password_hash=hash_password(password),
            is_active=True,
            is_superuser=False,
        )
        db_session.add(user)
        await db_session.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            "/api/v1/auth/login",
            json={"username": username, "user_pwd": login_password},
        )
        return response


async def _run_login_nonexistent(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            "/api/v1/auth/login",
            json={"username": "nonexistent", "user_pwd": "anything"},
        )
        return response


async def _run_get_me_no_auth(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/v1/auth/me")
        return response


def test_login_success(app) -> None:
    """Valid credentials return an access token."""
    response = anyio.run(
        _create_user_and_login,
        app,
        None,
        "test@example.com",
        "pass123",
        "pass123",
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


def test_login_invalid_password(app) -> None:
    """Invalid credentials return 401 without user enumeration."""
    response = anyio.run(
        _create_user_and_login,
        app,
        None,
        "test2@example.com",
        "pass123",
        "wrongpass",
    )
    assert response.status_code == 401


def test_login_nonexistent_user(app) -> None:
    """Login with nonexistent user returns 401."""
    response = anyio.run(_run_login_nonexistent, app)
    assert response.status_code == 401


def test_get_me_requires_auth(app) -> None:
    """Getting current user without auth returns 401."""
    response = anyio.run(_run_get_me_no_auth, app)
    assert response.status_code == 401
