"""FastAPI application factory and route registration.

Creates the JARVIS API application with lifespan management, health
endpoints, authentication routes, and global error handling.
"""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse

from jarvis.api.agent_runtime import router as agent_runtime_router
from jarvis.api.agents import router as agents_router
from jarvis.api.approvals import router as approvals_router
from jarvis.api.audit import router as audit_router
from jarvis.api.auth import router as auth_router
from jarvis.api.conversations import router as conversations_router
from jarvis.api.health import router as health_router
from jarvis.api.memory import router as memory_router
from jarvis.api.models import router as models_router
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
from jarvis.ui.routes import router as ui_router

logger = get_logger(__name__)

APP_VERSION = "0.1.0"

# Rate-limit storage: {client_key: [timestamps]}
_RATE_LIMIT_STORE: dict[str, list[float]] = {}
_RATE_LIMIT_MAX_REQUESTS = 60
_RATE_LIMIT_WINDOW_SECONDS = 60


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
    async def jarvis_error_handler(request: Request, exc: JarvisError) -> JSONResponse:
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

    # Security headers + rate limiting middleware.
    @app.middleware("http")
    async def security_and_metrics_middleware(
        request: Request, call_next: Callable[[Request], Awaitable[JSONResponse]]
    ) -> JSONResponse:
        # Rate limiting (applies to all endpoints except health/metrics)
        path = request.url.path
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
    app.include_router(models_router)
    app.include_router(approvals_router)
    app.include_router(audit_router)
    app.include_router(agents_router)
    app.include_router(tasks_router)
    app.include_router(voice_router)
    app.include_router(vision_router)
    app.include_router(agent_runtime_router)
    app.include_router(smart_environment_router)
    app.include_router(ui_router)

    logger.info(
        "JARVIS application created",
        extra={"env": settings.app_env, "version": APP_VERSION},
    )

    return app
