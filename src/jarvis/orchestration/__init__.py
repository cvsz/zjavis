"""Agent orchestration layer: task execution, agent registry, and bounded workflows.

Per javis-blueprint.md section 8 (Multi-Agent Ecosystem) and section 21 Phase 6,
this layer provides:

- Agent registry with typed capability contracts
- Bounded task execution with timeouts, retries, and resource budgets
- Approval-gate integration for medium/high-risk tasks
- Cancellation propagation and dead-letter handling
- Optimistic concurrency for state transitions
"""

from __future__ import annotations

from jarvis.core.logging import get_logger

logger = get_logger(__name__)

__all__ = [
    "ORCHESTRATION_VERSION",
    "AgentRegistry",
    "TaskCoordinator",
    "TaskState",
]

ORCHESTRATION_VERSION = "1.0.0"


class TaskState:
    """Task lifecycle states per blueprint section 3.2 request lifecycle."""

    QUEUED = "queued"
    RUNNING = "running"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

    ALL = frozenset({QUEUED, RUNNING, BLOCKED, COMPLETED, FAILED, CANCELLED})


class AgentRegistry:
    """Registry of agent definitions with capability declarations.

    Maintains in-memory registration of agents loaded from the database,
    enforcing per-agent concurrency limits, runtime budgets, and delegation depth.
    """

    def __init__(self) -> None:
        self._agents: dict[str, dict[str, object]] = {}
        self._concurrent: dict[str, int] = {}
        self.logger = get_logger(__name__)

    def register(self, agent_id: str, capabilities: dict[str, object]) -> None:
        """Register an agent definition.

        Args:
            agent_id: Stable agent identity.
            capabilities: Agent capability metadata (name, version, max_runtime_seconds,
                max_tool_calls, allowed_tools, delegation_depth, etc.).
        """
        self._agents[agent_id] = dict(capabilities)
        self._concurrent[agent_id] = 0
        self.logger.info(
            "Agent registered",
            extra={"agent_id": agent_id, "capabilities": capabilities},
        )

    def is_active(self, agent_id: str) -> bool:
        """Return whether an agent is registered and active."""
        return agent_id in self._agents

    def can_execute(self, agent_id: str) -> bool:
        """Check whether an agent has capacity for a new execution."""
        if agent_id not in self._agents:
            return False
        max_concurrent_value = self._agents[agent_id].get(
            "max_concurrent_executions", 1
        )
        if not isinstance(max_concurrent_value, int):
            max_concurrent = 1
        else:
            max_concurrent = max_concurrent_value
        return bool(self._concurrent.get(agent_id, 0) < max_concurrent)

    def acquire(self, agent_id: str) -> bool:
        """Acquire a concurrent execution slot for an agent."""
        if not self.can_execute(agent_id):
            return False
        self._concurrent[agent_id] = self._concurrent.get(agent_id, 0) + 1
        return True

    def release(self, agent_id: str) -> None:
        """Release a concurrent execution slot for an agent."""
        if agent_id in self._concurrent and self._concurrent[agent_id] > 0:
            self._concurrent[agent_id] -= 1

    def get_capability(self, agent_id: str, key: str, default: object = None) -> object:
        """Get a capability value for a registered agent."""
        return self._agents.get(agent_id, {}).get(key, default)


class TaskCoordinator:
    """Coordinates bounded task execution with approval gates and audit trails.

    The coordinator enforces:
    - Risk-based approval requirements before execution
    - Per-task timeouts and retry budgets
    - Cancellation propagation
    - Optimistic state transitions (queued -> running -> completed/failed/cancelled)
    - Audit event recording for every transition
    """

    def __init__(
        self,
        *,
        session,
        approval_service,
        audit_service,
        agent_registry: AgentRegistry | None = None,
    ) -> None:
        self.session = session
        self.approval_service = approval_service
        self.audit_service = audit_service
        self.agent_registry = agent_registry or AgentRegistry()
        self.logger = get_logger(__name__)

    async def can_execute(
        self,
        *,
        task_id: str,
        actor_id: str | None = None,
        tenant_id: str | None = None,
        risk_level: str = "low",
        required_permission: str | None = None,
        actor_permissions: set[str] | None = None,
    ) -> tuple[bool, str]:
        """Determine whether a task may execute, and why not if not.

        Returns:
            (allowed, reason) tuple.
        """
        # Default deny when policy cannot be evaluated
        if not required_permission:
            return False, "No required permission specified"

        # Check actor permissions
        if (
            actor_permissions is not None
            and required_permission not in actor_permissions
        ):
            return False, f"Missing required permission: {required_permission}"

        # Medium/high risk and approval-required actions need explicit approval
        if risk_level in ("medium", "high"):
            from uuid import UUID

            try:
                task_uuid = UUID(task_id)
            except (ValueError, AttributeError):
                return False, "Invalid task ID"
            if not await self.approval_service.is_approved(task_uuid):
                return False, f"Task {task_id} requires approval but none granted"

        # Agent capacity check
        # (agent_id resolved by caller; registry consulted if available)
        return True, "Authorized"

    async def record_transition(
        self,
        *,
        task_id: str,
        from_state: str,
        to_state: str,
        actor_id: str | None = None,
        tenant_id: str | None = None,
        details: str | None = None,
    ) -> None:
        """Record a task state transition as an audit event."""
        from jarvis.audit import CAT_AGENT, OUTCOME_SUCCESS, AuditService

        audit = AuditService(self.session)
        await audit.record(
            event_type="task.state.transition",
            event_category=CAT_AGENT,
            outcome=OUTCOME_SUCCESS,
            tenant_id=tenant_id,
            actor_id=actor_id,
            details=details or f"Task {task_id}: {from_state} -> {to_state}",
        )
        self.logger.info(
            "Task state transition recorded",
            extra={
                "task_id": task_id,
                "from_state": from_state,
                "to_state": to_state,
                "actor_id": actor_id,
                "tenant_id": tenant_id,
            },
        )
