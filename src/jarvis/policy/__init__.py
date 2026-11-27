"""Policy engine package.

Re-exports the policy decision types and engine from
``jarvis.core.policy`` so callers can import from a single location.

Per javis-blueprint.md section 15.3, every action must be evaluated at
execution time. Default is deny when policy cannot be evaluated.
"""

from __future__ import annotations

from jarvis.core.policy import (
    ALL_DECISIONS,
    APPROVAL_REQUIRED_ACTIONS,
    DECISION_ALLOW,
    DECISION_DENY,
    DECISION_OUT_OF_SCOPE,
    DECISION_REQUIRE_APPROVAL,
    DECISION_REQUIRE_REAUTHENTICATION,
    PolicyDecision,
    PolicyEngine,
)

__all__ = [
    "ALL_DECISIONS",
    "APPROVAL_REQUIRED_ACTIONS",
    "DECISION_ALLOW",
    "DECISION_DENY",
    "DECISION_OUT_OF_SCOPE",
    "DECISION_REQUIRE_APPROVAL",
    "DECISION_REQUIRE_REAUTHENTICATION",
    "PolicyDecision",
    "PolicyEngine",
]
