"""Unit tests for the JARVIS policy engine."""

from __future__ import annotations

from jarvis.core.policy import (
    DECISION_ALLOW,
    DECISION_DENY,
    DECISION_OUT_OF_SCOPE,
    DECISION_REQUIRE_APPROVAL,
    PolicyEngine,
)


def test_policy_engine_allows_granted_permission() -> None:
    """Policy engine returns ALLOW when actor holds required permission."""
    engine = PolicyEngine()
    decision = engine.evaluate(
        actor_permissions={"repository.read"},
        required_permission="repository.read",
        action="read repository",
    )
    assert decision.decision == DECISION_ALLOW
    assert decision.allowed is True
    assert decision.denied is False


def test_policy_engine_denies_missing_permission() -> None:
    """Policy engine returns DENY when actor lacks required permission."""
    engine = PolicyEngine()
    decision = engine.evaluate(
        actor_permissions={"repository.read"},
        required_permission="database.mutate",
        action="mutate database",
    )
    assert decision.decision == DECISION_DENY
    assert decision.allowed is False
    assert decision.denied is True


def test_policy_engine_denies_unknown_permission() -> None:
    """Policy engine returns OUT_OF_SCOPE for unrecognized permissions."""
    engine = PolicyEngine()
    decision = engine.evaluate(
        actor_permissions={"repository.read"},
        required_permission="nonexistent.permission",
        action="do something unknown",
    )
    assert decision.decision == DECISION_OUT_OF_SCOPE
    assert decision.denied is True


def test_policy_engine_requires_approval_for_high_risk() -> None:
    """Policy engine returns REQUIRE_APPROVAL for high-risk actions."""
    engine = PolicyEngine()
    decision = engine.evaluate(
        actor_permissions={"database.mutate"},
        required_permission="database.mutate",
        action="mutate database",
        risk_level="high",
    )
    assert decision.decision == DECISION_REQUIRE_APPROVAL
    assert decision.requires_approval is True


def test_policy_engine_requires_approval_for_approval_required_permission() -> None:
    """Policy engine returns REQUIRE_APPROVAL for deployment.execute."""
    engine = PolicyEngine()
    decision = engine.evaluate(
        actor_permissions={"deployment.execute"},
        required_permission="deployment.execute",
        action="deploy to production",
        risk_level="low",
    )
    assert decision.decision == DECISION_REQUIRE_APPROVAL


def test_policy_engine_default_deny() -> None:
    """Policy engine denies when no required permission is specified."""
    engine = PolicyEngine()
    decision = engine.evaluate(
        actor_permissions={"repository.read"},
        required_permission="",
        action="unspecified action",
    )
    assert decision.decision == DECISION_DENY
