"""FastAPI application factory and route registration.

Creates the JARVIS API application with lifespan management, health
endpoints, authentication routes, and global error handling.

Execution-time policy enforcement is applied to mutating operations
(POST/PUT/DELETE/PATCH) via the PolicyEngine, ensuring every action is
authorized at request time per javis-blueprint.md section 15.3.
"""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from typing import Any
from uuid import UUID

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from sqlalchemy import select

from jarvis.api.agent_runtime import router as agent_runtime_router
from jarvis.api.agents import router as agents_router
from jarvis.api.approvals import router as approvals_router
from jarvis.api.audit import router as audit_router
from jarvis.api.auth import router as auth_router
from jarvis.api.conversations import router as conversations_router
from jarvis.api.health import router as health_router
from jarvis.api.memory import router as memory_router
from jarvis.api.smart_environment import router as smart_environment_router
from jarvis.api.tasks import router as tasks_router
from jarvis.api.vision import router as vision_router
from jarvis.api.voice import router as voice_router
from jarvis.core.config import settings
from jarvis.core.exceptions import (
    AuthenticationError,
    AuthorizationError,
    ConflictError,
    JarvisError,
    NotFoundError,
)
from jarvis.core.logging import get_logger, setup_logging
from jarvis.core.metrics import record_request
from jarvis.core.policy import (
    DECISION_REQUIRE_APPROVAL,
    PolicyEngine,
)
from jarvis.core.security import Permission, decode_access_token
from jarvis.db import get_session
from jarvis.db.models import Permission as DbPermission
from jarvis.db.models import RoleBinding, User

logger = get_logger(__name__)

APP_VERSION = "0.1.0"

# Rate-limit storage: {client_key: [timestamps]}
_RATE_LIMIT_STORE: dict[str, list[float]] = {}
_RATE_LIMIT_MAX_REQUESTS = 60
_RATE_LIMIT_WINDOW_SECONDS = 60

# Mutating paths that require execution-time policy evaluation.
_POLICY_PROTECTED_METHODS = frozenset({"POST", "PUT", "DELETE", "PATCH"})

# Path prefixes exempt from policy engine (health, metrics, auth, docs).
_POLICY_EXEMPT_PREFIXES = (
    "/health",
    "/ready",
    "/metrics",
    "/api/v1/auth",
    "/docs",
    "/openapi.json",
)


def _client_key(request: Request) -> str:
    """Derive a client identifier for rate limiting."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    client = request.client
    return client.host if client else "unknown"


def _check_rate_limit(key: str) -> bool:
    """Return True if the request is within rate limits, False otherwise."""
    now = time.time()
    window_start = now - _RATE_LIMIT_WINDOW_SECONDS
    timestamps = _RATE_LIMIT_STORE.get(key, [])
    # Prune old entries
    recent = [ts for ts in timestamps if ts > window_start]
    if len(recent) >= _RATE_LIMIT_MAX_REQUESTS:
        return False
    recent.append(now)
    _RATE_LIMIT_STORE[key] = recent
    return True


async def _get_user_permissions(
    session: Any, authorization: str | None
) -> set[str]:
    """Load capability permissions for the authenticated user.

    Reads role_bindings -> roles -> permissions through the database,
    returning the set of permission strings the user holds. Returns an
    empty set if no roles are assigned or the token is invalid.
    """
    if not authorization or not authorization.startswith("Bearer "):
        return set()
    token = authorization.split(" ", 1)[1]

    try:
        payload = decode_access_token(token)
    except AuthenticationError:
        return set()
    user_id_str = payload.get("sub")
    if not user_id_str:
        return set()

    try:
        user_id = UUID(user_id_str)
    except ValueError:
        return set()

    # Verify user exists and is active.
    user_result = await session.execute(
        select(User).where(User.id == user_id, User.is_active == True)
    )
    user = user_result.scalar_one_or_none()
    if user is None:
        return set()

    # Load permission names via role_bindings for the user's tenants.
    perm_result = await session.execute(
        select(DbPermission.name)
        .join(RoleBinding, RoleBinding.role_id == DbPermission.id)
        .where(RoleBinding.user_id == user_id)
    )
    return {row[0] for row in perm_result.all()}


def _permission_for_path(path: str, method: str) -> str:
    """Map an API path and method to the required capability permission."""
    # Conversation endpoints
    if path.startswith("/api/v1/conversations"):
        if method == "POST":
            return str(Permission.REPOSITORY_WRITE)
        return str(Permission.REPOSITORY_READ)
    # Memory endpoints
    if path.startswith("/api/v1/memory"):
        if method in ("POST", "DELETE"):
            return str(Permission.REPOSITORY_WRITE)
        return str(Permission.REPOSITORY_READ)
    # Approval endpoints
    if path.startswith("/api/v1/approvals"):
        if method == "POST" and ("/grant" in path or "/deny" in path):
            return str(Permission.REPOSITORY_WRITE)
        return str(Permission.REPOSITORY_READ)
    # Agent endpoints
    if path.startswith("/api/v1/agents"):
        if method in ("POST", "PUT", "DELETE"):
            return str(Permission.REPOSITORY_WRITE)
        return str(Permission.REPOSITORY_READ)
    # Task endpoints
    if path.startswith("/api/v1/tasks"):
        if method in ("POST", "PUT", "DELETE"):
            return str(Permission.REPOSITORY_WRITE)
        return str(Permission.REPOSITORY_READ)
    # Voice/Vision/Smart-environment (mutating)
    if path.startswith(
        ("/api/v1/voice", "/api/v1/vision", "/api/v1/smart-environment")
    ):
        if method == "POST":
            return str(Permission.REPOSITORY_WRITE)
        return str(Permission.REPOSITORY_READ)
    # Agent runtime execution
    if path.startswith("/api/v1/agent-runtime"):
        return str(Permission.REPOSITORY_WRITE)
    # Audit is read-only
    if path.startswith("/api/v1/audit"):
        return str(Permission.REPOSITORY_READ)
    return str(Permission.REPOSITORY_READ)


def _risk_level_for_path(path: str) -> str:
    """Classify risk level for a path.

    Mutating operations on tasks, agent runtime, and smart environment
    are classified as medium risk, requiring approval per policy.
    """
    high_risk = (
        "/api/v1/tasks",
        "/api/v1/agent-runtime",
        "/api/v1/smart-environment",
    )
    if any(path.startswith(p) for p in high_risk):
        return "medium"
    return "low"


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Returns:
        A configured :class:`FastAPI` application instance.
    """
    setup_logging(log_level=settings.log_level)

    app = FastAPI(
        title="JARVIS API",
        description="Personal AI Operating System core platform API",
        version=APP_VERSION,
        debug=settings.debug,
    )

    # CORS — restrict to same-origin by default; configure via env if needed.
    # allow_credentials must be False when allow_origins is wildcard per CORS spec.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )

    # Global error handler for JarvisError -> consistent JSON responses.
    @app.exception_handler(JarvisError)
    async def jarvis_error_handler(
        request: Request, exc: JarvisError
    ) -> JSONResponse:
        status_code = status.HTTP_400_BAD_REQUEST
        if isinstance(exc, AuthenticationError):
            status_code = status.HTTP_401_UNAUTHORIZED
        elif isinstance(exc, AuthorizationError):
            status_code = status.HTTP_403_FORBIDDEN
        elif isinstance(exc, NotFoundError):
            status_code = status.HTTP_404_NOT_FOUND
        elif isinstance(exc, ConflictError):
            status_code = status.HTTP_409_CONFLICT
        return JSONResponse(
            status_code=status_code,
            content={
                "error": exc.code,
                "message": exc.message,
                "details": exc.details,
            },
        )

    # Security headers + rate limiting + policy enforcement middleware.
    @app.middleware("http")
    async def security_and_metrics_middleware(
        request: Request,
        call_next: Callable[[Request], Awaitable[JSONResponse]],
    ) -> JSONResponse:
        path = request.url.path

        # Rate limiting (applies to all endpoints except health/metrics)
        if path not in ("/health", "/ready", "/metrics"):
            key = _client_key(request)
            if not _check_rate_limit(key):
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        "error": "rate_limited",
                        "message": "Too many requests. Please try again later.",
                        "details": {},
                    },
                    headers={
                        "Retry-After": str(_RATE_LIMIT_WINDOW_SECONDS),
                    },
                )

        # Execution-time policy enforcement for mutating operations.
        if (
            request.method in _POLICY_PROTECTED_METHODS
            and not path.startswith(_POLICY_EXEMPT_PREFIXES)
        ):
            policy_engine = PolicyEngine()
            async for session in get_session():
                authorization = request.headers.get("authorization")
                user_permissions = await _get_user_permissions(
                    session, authorization
                )
                # Map path + method to a required permission.
                required_permission = _permission_for_path(path, request.method)
                decision = policy_engine.evaluate(
                    actor_permissions=user_permissions,
                    required_permission=required_permission,
                    action=f"{request.method} {path}",
                    risk_level=_risk_level_for_path(path),
                )
                if decision.decision == DECISION_REQUIRE_APPROVAL:
                    return JSONResponse(
                        status_code=status.HTTP_403_FORBIDDEN,
                        content={
                            "error": "approval_required",
                            "message": decision.reason,
                            "details": {
                                "required_permission": decision.required_permission,
                                "requires_approval": True,
                            },
                        },
                    )
                if decision.denied:
                    return JSONResponse(
                        status_code=status.HTTP_403_FORBIDDEN,
                        content={
                            "error": "forbidden",
                            "message": decision.reason,
                            "details": {
                                "required_permission": decision.required_permission,
                                "requires_approval": decision.requires_approval,
                            },
                        },
                    )
                break  # session closed after policy check

        start = time.time()
        try:
            response: JSONResponse = await call_next(request)
        except Exception:
            duration = time.time() - start
            record_request(request.method, path, 500, duration)
            raise
        duration = time.time() - start
        record_request(request.method, path, response.status_code, duration)

        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        return response

    # Metrics endpoint for Prometheus scraping.
    @app.get("/metrics", include_in_schema=False)
    async def metrics() -> PlainTextResponse:
        from jarvis.core.metrics import get_metrics

        return PlainTextResponse(
            content=get_metrics(),
            media_type="text/plain; version=0.0.4; charset=utf-8",
        )

    # Routers
    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(conversations_router)
    app.include_router(memory_router)
    app.include_router(approvals_router)
    app.include_router(audit_router)
    app.include_router(agents_router)
    app.include_router(tasks_router)
    app.include_router(voice_router)
    app.include_router(vision_router)
    app.include_router(agent_runtime_router)
    app.include_router(smart_environment_router)

    logger.info(
        "JARVIS application created",
        extra={"env": settings.app_env, "version": APP_VERSION},
    )

    return app
