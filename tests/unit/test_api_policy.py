"""Unit tests for policy enforcement on API routes.

Verifies that the ``require_policy`` dependency correctly authenticates
users and enforces execution-time policy decisions (ALLOW / DENY /
REQUIRE_APPROVAL / OUT_OF_SCOPE) using the PolicyEngine.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from jarvis.auth import require_policy
from jarvis.core.exceptions import AuthorizationError
from jarvis.core.policy import (
    APPROVAL_REQUIRED_ACTIONS,
    DECISION_ALLOW,
    DECISION_DENY,
    DECISION_OUT_OF_SCOPE,
    DECISION_REQUIRE_APPROVAL,
    PolicyEngine,
)
from jarvis.core.security import Permission


class TestPolicyEngineDecisions:
    """Direct tests of PolicyEngine decision outcomes."""

    def test_engine_allows_granted_permission(self) -> None:
        engine = PolicyEngine()
        decision = engine.evaluate(
            actor_permissions={"repository.read"},
            required_permission="repository.read",
            action="read repository",
        )
        assert decision.decision == DECISION_ALLOW
        assert decision.allowed is True

    def test_engine_denies_missing_permission(self) -> None:
        engine = PolicyEngine()
        decision = engine.evaluate(
            actor_permissions={"repository.read"},
            required_permission="database.mutate",
            action="mutate database",
        )
        assert decision.decision == DECISION_DENY
        assert decision.denied is True

    def test_engine_out_of_scope(self) -> None:
        engine = PolicyEngine()
        decision = engine.evaluate(
            actor_permissions={"repository.read"},
            required_permission="nonexistent.permission",
            action="do something unknown",
        )
        assert decision.decision == DECISION_OUT_OF_SCOPE
        assert decision.denied is True

    def test_engine_requires_approval_high_risk(self) -> None:
        engine = PolicyEngine()
        decision = engine.evaluate(
            actor_permissions={"database.mutate"},
            required_permission="database.mutate",
            action="mutate database",
            risk_level="high",
        )
        assert decision.decision == DECISION_REQUIRE_APPROVAL
        assert decision.requires_approval is True

    def test_engine_requires_approval_approval_required_action(self) -> None:
        engine = PolicyEngine()
        decision = engine.evaluate(
            actor_permissions={"deployment.execute"},
            required_permission="deployment.execute",
            action="deploy to production",
            risk_level="low",
        )
        assert decision.decision == DECISION_REQUIRE_APPROVAL

    def test_engine_default_deny(self) -> None:
        engine = PolicyEngine()
        decision = engine.evaluate(
            actor_permissions={"repository.read"},
            required_permission="",
            action="unspecified action",
        )
        assert decision.decision == DECISION_DENY


class TestRequirePolicyDependency:
    """Tests for the require_policy FastAPI dependency."""

    def _make_dependency_mock(
        self,
        user_permissions: set[str] | None = None,
        decision_override: Any = None,
    ) -> tuple[MagicMock, MagicMock]:
        """Build a mocked session and user for dependency testing."""
        session = AsyncMock()
        user = MagicMock()
        user.id = "00000000-0000-0000-0000-000000000001"
        user.is_active = True

        # Mock get_current_user to return our user
        # We'll patch it at the call site instead

        result = MagicMock()
        if user_permissions is not None:
            result.all = lambda: [(p,) for p in user_permissions]
        else:
            result.all = lambda: []  # noqa: PIE807 — intentional mock method, not a constant list
        session.execute.return_value = result

        return session, user

    @pytest.mark.asyncio
    async def test_require_policy_allows_when_permission_held(self) -> None:
        """Dependency returns the user when policy evaluates to ALLOW."""
        from unittest.mock import patch

        session, user = self._make_dependency_mock(user_permissions={"repository.read"})

        with patch("jarvis.auth.get_current_user", new=AsyncMock(return_value=user)):
            dep = require_policy(
                required_permission="repository.read",
                action="read repository",
                risk_level="low",
            )
            result = await dep(session=session, authorization="Bearer token")
            assert result is user

    @pytest.mark.asyncio
    async def test_require_policy_denies_when_permission_missing(self) -> None:
        """Dependency raises 403 when policy evaluates to DENY."""
        from unittest.mock import patch

        session, user = self._make_dependency_mock(user_permissions={"repository.read"})

        with patch("jarvis.auth.get_current_user", new=AsyncMock(return_value=user)):
            dep = require_policy(
                required_permission="database.mutate",
                action="mutate database",
                risk_level="low",
            )
            with pytest.raises(AuthorizationError) as exc_info:
                await dep(session=session, authorization="Bearer token")
            assert exc_info.value.code == "insufficient_permission"

    @pytest.mark.asyncio
    async def test_require_policy_requires_approval(self) -> None:
        """Dependency raises 403 when policy evaluates to REQUIRE_APPROVAL."""
        from unittest.mock import patch

        session, user = self._make_dependency_mock(user_permissions={"database.mutate"})

        with patch("jarvis.auth.get_current_user", new=AsyncMock(return_value=user)):
            dep = require_policy(
                required_permission="database.mutate",
                action="mutate database",
                risk_level="high",
            )
            with pytest.raises(AuthorizationError) as exc_info:
                await dep(session=session, authorization="Bearer token")
            assert exc_info.value.code == "approval_required"

    @pytest.mark.asyncio
    async def test_require_policy_no_permission_required(self) -> None:
        """Dependency returns the user when no permission is required."""
        from unittest.mock import patch

        session, user = self._make_dependency_mock()

        with patch("jarvis.auth.get_current_user", new=AsyncMock(return_value=user)):
            dep = require_policy()
            result = await dep(session=session, authorization="Bearer token")
            assert result is user


class TestPermissionConstants:
    """Tests that all expected permission constants are defined."""

    def test_all_permissions_defined(self) -> None:
        perms = Permission.all()
        assert Permission.READ in perms
        assert Permission.REPOSITORY_READ in perms
        assert Permission.REPOSITORY_WRITE in perms
        assert Permission.DATABASE_MUTATE in perms
        assert Permission.DEPLOYMENT_EXECUTE in perms
        assert len(perms) > 0

    def test_approval_required_actions(self) -> None:
        assert Permission.DATABASE_MUTATE in APPROVAL_REQUIRED_ACTIONS
        assert Permission.DEPLOYMENT_EXECUTE in APPROVAL_REQUIRED_ACTIONS
