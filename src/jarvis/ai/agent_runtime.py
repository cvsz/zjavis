"""Agent runtime: autonomous agent execution engine.

Per JARVIS blueprint, agent capabilities are gated behind the
``agent_runtime_enabled`` configuration flag. The runtime executes
tasks using agents, checks approval gates for high-risk tasks, and
records outcomes via audit events.

All task state transitions are delegated to the ``OrchestrationEngine``
state machine so that queued -> running -> completed/failed/blocked/
cancelled transitions are validated, retries use exponential backoff
with jitter, cancellation is honoured, and delegation depth is bounded.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from jarvis.ai.gateway import gateway
from jarvis.approval import ApprovalService
from jarvis.audit import CAT_AGENT, OUTCOME_FAILURE, OUTCOME_SUCCESS, AuditService
from jarvis.core.exceptions import NotFoundError
from jarvis.core.logging import get_logger
from jarvis.db.models import Agent, Task
from jarvis.orchestration import OrchestrationEngine, TaskContext

logger = get_logger(__name__)


class AgentRuntime:
    """Executes tasks using registered agents.

    The runtime:
    - Loads agent and task definitions from the database
    - Checks approval gates for medium/high risk tasks
    - Generates AI responses via the model gateway
    - Records execution outcomes as audit events
    - Delegates task state lifecycle to the OrchestrationEngine
    """

    def __init__(
        self,
        *,
        session: AsyncSession,
        enabled: bool = False,
    ) -> None:
        self.session = session
        self.enabled = enabled

    def _require_enabled(self) -> None:
        if not self.enabled:
            raise RuntimeError(
                "Agent runtime is disabled. Set JARVIS_AGENT_RUNTIME_ENABLED=true to enable."
            )

    def _uuid(self, value: Any) -> UUID | None:
        """Convert a Column[UUID] or UUID to a plain UUID value."""
        return UUID(str(value)) if value is not None else None

    async def _load_agent(self, agent_id: UUID) -> Agent:
        result = await self.session.execute(select(Agent).where(Agent.id == agent_id))
        agent = result.scalar_one_or_none()
        if agent is None:
            raise NotFoundError(f"Agent not found: {agent_id}")
        return agent

    async def _load_task(self, task_id: UUID) -> Task:
        result = await self.session.execute(select(Task).where(Task.id == task_id))
        task = result.scalar_one_or_none()
        if task is None:
            raise NotFoundError(f"Task not found: {task_id}")
        return task

    async def _requires_approval(self, task: Task) -> bool:
        """High and medium risk tasks require approval."""
        return task.risk_classification in ("medium", "high")

    async def _is_approved(self, task: Task) -> bool:
        approval_service = ApprovalService(self.session)
        task_uuid = self._uuid(task.id)
        if task_uuid is None:
            return False
        return bool(await approval_service.is_approved(task_uuid))

    async def _record_audit(
        self,
        *,
        event_type: str,
        outcome: str,
        tenant_id: UUID | None,
        actor_id: UUID | None,
        details: str | None = None,
    ) -> None:
        audit_service = AuditService(self.session)
        await audit_service.record(
            event_type=event_type,
            event_category=CAT_AGENT,
            outcome=outcome,
            tenant_id=tenant_id,
            actor_id=actor_id,
            details=details,
        )

    async def execute_task(
        self,
        task_id: UUID,
        *,
        tenant_id: UUID | None = None,
        user_id: UUID | None = None,
    ) -> dict[str, Any]:
        """Execute a task through the agent runtime.

        Args:
            task_id: The task to execute.
            tenant_id: Tenant ID to scope the task to (enforced when provided).
            user_id: User ID to scope the task to (enforced when provided).

        Returns:
            Dict with execution result details.

        Raises:
            RuntimeError: If agent runtime is disabled.
            NotFoundError: If agent or task not found.
            AuthorizationError: If the task does not belong to the scoped
                tenant/user (tenant isolation violation).
        """
        self._require_enabled()

        task = await self._load_task(task_id)

        # Enforce tenant isolation: the task must belong to the caller's
        # tenant when a tenant scope is provided.
        if tenant_id is not None and str(task.tenant_id) != str(tenant_id):
            from jarvis.core.exceptions import AuthorizationError

            raise AuthorizationError(
                "Task does not belong to the requesting tenant",
                code="tenant_isolation_violation",
                details={
                    "task_id": str(task_id),
                    "task_tenant_id": str(task.tenant_id),
                    "requested_tenant_id": str(tenant_id),
                },
            )

        # Enforce user ownership when a user scope is provided.
        if user_id is not None and str(task.user_id) != str(user_id):
            from jarvis.core.exceptions import AuthorizationError

            raise AuthorizationError(
                "Task does not belong to the requesting user",
                code="user_ownership_violation",
                details={
                    "task_id": str(task_id),
                    "task_user_id": str(task.user_id),
                    "requested_user_id": str(user_id),
                },
            )

        agent: Agent | None = None
        if task.agent_id is not None:
            agent_id = self._uuid(task.agent_id)
            if agent_id is not None:
                agent = await self._load_agent(agent_id)
                if not agent.is_active:
                    raise PermissionError(f"Agent {agent.id} is not active")

        # Approval gate for risk tasks
        if await self._requires_approval(task) and not await self._is_approved(task):
            await self._record_audit(
                event_type="task.execution.blocked",
                outcome="denial",
                tenant_id=self._uuid(task.tenant_id),
                actor_id=self._uuid(task.user_id),
                details=f"Task {task_id} requires approval but none granted",
            )
            raise PermissionError(f"Task {task_id} requires approval before execution")

        tenant_id = self._uuid(task.tenant_id)
        user_id = self._uuid(task.user_id)

        # Build system prompt once (closure over agent info for the handler).
        agent_name = agent.name if agent else "default"
        system_prompt = (
            f"You are an autonomous agent ({agent_name}). "
            f"Execute the following task: {task.task_type!s}. "
            f"Risk classification: {task.risk_classification!s}."
        )
        user_content = (
            f"Task: {task.task_type!s}\nDetails: Execute using available tools."
        )

        engine = OrchestrationEngine(session=self.session)

        async def _handler(ctx: TaskContext) -> str:
            """Handler executed by the OrchestrationEngine once state is 'running'."""
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ]
            result = await gateway.complete(
                task_type=str(task.task_type),
                messages=messages,
            )
            return str(result.get("response", ""))

        try:
            result = await engine.execute(
                task_id=task_id,
                handler=_handler,
                delegation_depth=0,
            )

            state = result["state"]
            response = result.get("response", "")

            if state == "completed":
                await self._record_audit(
                    event_type="task.execution.completed",
                    outcome=OUTCOME_SUCCESS,
                    tenant_id=tenant_id,
                    actor_id=user_id,
                    details=f"Task {task_id} completed successfully",
                )
                logger.info(
                    "Task executed via orchestration engine",
                    extra={
                        "task_id": str(task_id),
                        "state": state,
                        "provider": result.get("provider"),
                        "model": result.get("model"),
                        "retries": result.get("retries"),
                    },
                )
                return {
                    "task_id": str(task_id),
                    "state": state,
                    "response": response,
                    "provider": result.get("provider"),
                    "model": result.get("model"),
                    "usage": result.get("usage", {}),
                    "retries": result.get("retries", 0),
                }

            if state == "failed":
                error = result.get("error", "Unknown error")
                await self._record_audit(
                    event_type="task.execution.failed",
                    outcome=OUTCOME_FAILURE,
                    tenant_id=tenant_id,
                    actor_id=user_id,
                    details=f"Task {task_id} failed: {error}",
                )
                logger.error(
                    "Task execution failed via orchestration engine",
                    extra={"task_id": str(task_id), "error": error},
                )
                raise RuntimeError(error)

            # cancelled or other terminal states
            return {
                "task_id": str(task_id),
                "state": state,
                "response": response,
                "provider": result.get("provider"),
                "model": result.get("model"),
                "usage": result.get("usage", {}),
                "retries": result.get("retries", 0),
            }

        except PermissionError:
            raise
        except RuntimeError:
            raise
        except Exception as exc:
            await self._record_audit(
                event_type="task.execution.failed",
                outcome=OUTCOME_FAILURE,
                tenant_id=tenant_id,
                actor_id=user_id,
                details=f"Task {task_id} failed: {exc}",
            )
            logger.error(
                "Task execution failed",
                extra={"task_id": str(task_id), "error": str(exc)},
            )
            raise
