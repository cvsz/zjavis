"""Unit tests for the JARVIS approvals API endpoints."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import ValidationError

from jarvis.api.approvals import ApprovalRequest
from jarvis.auth import require_policy
from jarvis.core.exceptions import AuthorizationError
from jarvis.core.security import Permission


class TestApprovalRequest:
    """Tests for ApprovalRequest model."""

    def test_approval_request_valid(self) -> None:
        import uuid

        req = ApprovalRequest(task_id=uuid.uuid4(), expires_in_minutes=60)
        assert req.expires_in_minutes == 60

    def test_approval_request_defaults(self) -> None:
        import uuid

        req = ApprovalRequest(task_id=uuid.uuid4())
        assert req.expires_in_minutes == 60

    def test_approval_request_expires_too_short(self) -> None:
        import uuid

        with pytest.raises(ValidationError):
            ApprovalRequest(task_id=uuid.uuid4(), expires_in_minutes=0)

    def test_approval_request_expires_too_long(self) -> None:
        import uuid

        with pytest.raises(ValidationError):
            ApprovalRequest(task_id=uuid.uuid4(), expires_in_minutes=10081)


class TestRequestApprovalPolicy:
    """Tests for policy enforcement on the request_approval endpoint.

    The request_approval endpoint now requires the
    ``deployment.request`` permission via ``require_policy()`` so that
    only authorized users can request approvals for consequential actions.
    """

    def _make_dependency_mock(
        self,
        user_permissions: set[str] | None = None,
    ) -> tuple[MagicMock, MagicMock]:
        """Build a mocked session and user for dependency testing."""
        session = AsyncMock()
        user = MagicMock()
        user.id = "00000000-0000-0000-0000-000000000001"
        user.is_active = True

        result = MagicMock()
        if user_permissions is not None:
            result.all = lambda: [(p,) for p in user_permissions]
        else:
            result.all = list
        session.execute.return_value = result

        return session, user

    @pytest.mark.asyncio
    async def test_request_approval_allows_when_deployment_request_held(
        self,
    ) -> None:
        """Dependency returns the user when policy evaluates to ALLOW."""
        from unittest.mock import patch

        session, user = self._make_dependency_mock(
            user_permissions={Permission.DEPLOYMENT_REQUEST}
        )

        with patch("jarvis.auth.get_current_user", new=AsyncMock(return_value=user)):
            dep = require_policy(
                required_permission=Permission.DEPLOYMENT_REQUEST,
                action="request approval",
                risk_level="medium",
            )
            result = await dep(session=session, authorization="Bearer token")
            assert result is user

    @pytest.mark.asyncio
    async def test_request_approval_denies_when_permission_missing(
        self,
    ) -> None:
        """Dependency raises 403 when policy evaluates to DENY."""
        from unittest.mock import patch

        session, user = self._make_dependency_mock(user_permissions={Permission.READ})

        with patch("jarvis.auth.get_current_user", new=AsyncMock(return_value=user)):
            dep = require_policy(
                required_permission=Permission.DEPLOYMENT_REQUEST,
                action="request approval",
                risk_level="medium",
            )
            with pytest.raises(AuthorizationError) as exc_info:
                await dep(session=session, authorization="Bearer token")
            assert exc_info.value.code == "insufficient_permission"
