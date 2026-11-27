"""End-to-end tests for JARVIS API user journeys.

These tests exercise complete user flows through the FastAPI application
using TestClient. Tests that require a live database are covered by
tests/integration/. Endpoints that require authenticated sessions with
tenant-scoped permission resolution are validated through the existing
integration test suite; this file focuses on flows that can be executed
reliably without external services (PostgreSQL is available locally).
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from jarvis.api.main import create_app
from jarvis.db import get_session


class _FakeResult:
    """Mock SQLAlchemy result object."""

    def __init__(self, value: Any = None) -> None:
        self._value = value

    def scalar_one_or_none(self) -> Any:
        return self._value

    def scalars(self) -> _FakeScalars:
        return _FakeScalars([self._value] if self._value is not None else [])


class _FakeScalars:
    def __init__(self, values: list[Any]) -> None:
        self._values = values

    def all(self) -> list[Any]:
        return self._values


class _FakeSession:
    """In-memory fake async session for E2E tests."""

    def __init__(self) -> None:
        self.added: list[Any] = []
        self.committed = False

    def add(self, obj: Any) -> None:
        self.added.append(obj)

    async def commit(self) -> None:
        self.committed = True

    async def refresh(self, obj: Any) -> None:
        pass

    async def execute(self, stmt: Any) -> _FakeResult:
        return _FakeResult(None)

    async def close(self) -> None:
        pass


def _make_app() -> TestClient:
    app = create_app()
    fake_session = _FakeSession()

    async def _override_get_session() -> AsyncSession:
        yield fake_session  # type: ignore[misc]

    app.dependency_overrides[get_session] = _override_get_session
    return TestClient(app)


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


class TestAuthFlow:
    """End-to-end authentication flow: login -> token -> profile."""

    @patch("jarvis.api.auth.authenticate_user")
    @patch("jarvis.api.auth.get_or_create_user_tenant")
    def test_login_and_me_flow(
        self,
        mock_tenant: MagicMock,
        mock_auth: MagicMock,
    ) -> None:
        """Login returns tokens; /me returns user profile."""
        client = _make_app()

        user = MagicMock()
        user.id = uuid4()
        user.username = "e2e_user"
        user.email = "e2e@example.com"
        user.is_active = True
        user.is_superuser = False

        mock_auth.return_value = user
        mock_tenant.return_value = MagicMock(id=uuid4())

        # Patch get_current_user at the module where the route imports it.
        with patch(
            "jarvis.api.auth.get_current_user",
            new=AsyncMock(return_value=user),
        ):
            # Login
            login_resp = client.post(
                "/api/v1/auth/login",
                json={"username": "e2e_user", "user_pwd": "password123"},
            )
            assert login_resp.status_code == 200, login_resp.text
            data = login_resp.json()
            assert "access_token" in data
            assert "refresh_token" in data
            assert data["token_type"] == "bearer"

            token = data["access_token"]

            # /me requires auth
            me_resp = client.get("/api/v1/auth/me", headers=_auth_headers(token))
            assert me_resp.status_code == 200, me_resp.text
            me_data = me_resp.json()
            assert me_data["username"] == "e2e_user"
            assert me_data["email"] == "e2e@example.com"

    def test_login_missing_credentials(self) -> None:
        """Login with missing body returns 422."""
        client = _make_app()
        resp = client.post("/api/v1/auth/login", json={})
        assert resp.status_code == 422, resp.text

    def test_me_without_auth(self) -> None:
        """Getting /me without auth returns 401."""
        client = _make_app()
        resp = client.get("/api/v1/auth/me")
        assert resp.status_code == 401, resp.text


class TestHealthAndMetrics:
    """End-to-end health and metrics endpoints."""

    def test_health_and_metrics(self) -> None:
        """Health and metrics endpoints are accessible."""
        client = _make_app()

        health_resp = client.get("/health")
        assert health_resp.status_code == 200, health_resp.text
        assert health_resp.json()["status"] == "alive"

        metrics_resp = client.get("/metrics")
        assert metrics_resp.status_code == 200, metrics_resp.text
        assert "jarvis_requests_total" in metrics_resp.text

    def test_ready_endpoint(self) -> None:
        """Readiness endpoint returns ready when database is reachable."""
        client = _make_app()
        resp = client.get("/ready")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["status"] == "ready"
        assert data["service"] == "jarvis"
        assert "checks" in data


class TestSecurityHeaders:
    """End-to-end security headers verification."""

    def test_security_headers_present(self) -> None:
        """All responses include security headers."""
        client = _make_app()
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.headers.get("X-Content-Type-Options") == "nosniff"
        assert resp.headers.get("X-Frame-Options") == "DENY"
        assert resp.headers.get("Referrer-Policy") == "no-referrer"
        assert "Content-Security-Policy" in resp.headers
