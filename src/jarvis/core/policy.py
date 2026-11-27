"""Policy engine: evaluates authorization decisions at execution time.

Per javis-blueprint.md section 15.3, every action must be evaluated at
execution time. The planner's assertion that an action is safe is not
authorization. Default is deny when policy cannot be evaluated.

Decision outcomes:
- ALLOW
- DENY
- REQUIRE_APPROVAL
- REQUIRE_REAUTHENTICATION
- OUT_OF_SCOPE
"""

from __future__ import annotations

from dataclasses import dataclass

from jarvis.core.logging import get_logger
from jarvis.core.security import Permission

logger = get_logger(__name__)

DECISION_ALLOW = "ALLOW"
DECISION_DENY = "DENY"
DECISION_REQUIRE_APPROVAL = "REQUIRE_APPROVAL"
DECISION_REQUIRE_REAUTHENTICATION = "REQUIRE_REAUTHENTICATION"
DECISION_OUT_OF_SCOPE = "OUT_OF_SCOPE"

ALL_DECISIONS = frozenset(
    {
        DECISION_ALLOW,
        DECISION_DENY,
        DECISION_REQUIRE_APPROVAL,
        DECISION_REQUIRE_REAUTHENTICATION,
        DECISION_OUT_OF_SCOPE,
    }
)

# Actions that always require explicit approval regardless of permissions.
APPROVAL_REQUIRED_ACTIONS = frozenset(
    {
        Permission.DEPLOYMENT_EXECUTE,
        Permission.DATABASE_MUTATE,
    }
)


@dataclass(frozen=True)
class PolicyDecision:
    """Result of a policy evaluation."""

    decision: str
    reason: str
    required_permission: str | None = None
    requires_approval: bool = False
    requires_reauthentication: bool = False
    metadata: dict[str, object] | None = None

    @property
    def allowed(self) -> bool:
        return self.decision == DECISION_ALLOW

    @property
    def denied(self) -> bool:
        return self.decision in (DECISION_DENY, DECISION_OUT_OF_SCOPE)


class PolicyEngine:
    """Evaluates authorization policies for requested actions.

    The engine is intentionally simple and explicit: it checks whether
    the actor holds the required permission, whether the action requires
    approval, and returns a structured decision. It does not make
    assertions about safety on behalf of callers.
    """

    def __init__(self) -> None:
        self.logger = get_logger(__name__)

    def evaluate(
        self,
        *,
        actor_permissions: set[str],
        required_permission: str,
        action: str,
        actor_id: str | None = None,
        tenant_id: str | None = None,
        risk_level: str = "low",
    ) -> PolicyDecision:
        """Evaluate a policy decision for the requested action.

        Args:
            actor_permissions: Permissions held by the requesting actor.
            required_permission: The permission required for this action.
            action: Human-readable description of the action.
            actor_id: ID of the acting principal.
            tenant_id: ID of the tenant context (for isolation checks).
            risk_level: Risk classification (low, medium, high, critical).

        Returns:
            A :class:`PolicyDecision` with the outcome.
        """
        # Default deny: if policy cannot be evaluated, deny.
        if not required_permission:
            self.logger.warning(
                "Policy evaluation denied: no required permission",
                extra={"action": action, "actor_id": actor_id, "tenant_id": tenant_id},
            )
            return PolicyDecision(
                decision=DECISION_DENY,
                reason="No required permission specified",
                required_permission=None,
            )

        # Out of scope: permission not recognized by the system.
        if required_permission not in Permission.all():
            self.logger.warning(
                "Policy evaluation: out of scope permission",
                extra={
                    "action": action,
                    "required_permission": required_permission,
                    "actor_id": actor_id,
                },
            )
            return PolicyDecision(
                decision=DECISION_OUT_OF_SCOPE,
                reason=f"Permission not recognized: {required_permission}",
                required_permission=required_permission,
            )

        # Check if the actor holds the required permission.
        if required_permission not in actor_permissions:
            self.logger.warning(
                "Policy evaluation: insufficient permission",
                extra={
                    "action": action,
                    "required_permission": required_permission,
                    "actor_permissions": sorted(actor_permissions),
                    "actor_id": actor_id,
                    "tenant_id": tenant_id,
                },
            )
            return PolicyDecision(
                decision=DECISION_DENY,
                reason=f"Missing required permission: {required_permission}",
                required_permission=required_permission,
            )

        # High-risk actions always require approval even with permission.
        if (
            risk_level in ("high", "critical")
            or required_permission in APPROVAL_REQUIRED_ACTIONS
        ):
            self.logger.info(
                "Policy evaluation: approval required",
                extra={
                    "action": action,
                    "required_permission": required_permission,
                    "risk_level": risk_level,
                    "actor_id": actor_id,
                },
            )
            return PolicyDecision(
                decision=DECISION_REQUIRE_APPROVAL,
                reason=f"Action requires approval: {action}",
                required_permission=required_permission,
                requires_approval=True,
            )

        self.logger.info(
            "Policy evaluation: allowed",
            extra={
                "action": action,
                "required_permission": required_permission,
                "actor_id": actor_id,
                "tenant_id": tenant_id,
            },
        )
        return PolicyDecision(
            decision=DECISION_ALLOW,
            reason="Authorized",
            required_permission=required_permission,
        )
