"""FastAPI application factory and route registration.

Creates the JARVIS API application with lifespan management, health
endpoints, authentication routes, and global error handling.
"""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse, PlainTextResponse

from jarvis.api.auth import router as auth_router
from jarvis.api.conversations import router as conversations_router
from jarvis.api.health import router as health_router
from jarvis.api.memory import router as memory_router
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

logger = get_logger(__name__)

APP_VERSION = "0.1.0"


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

    # Metrics middleware: record request rate and latency per endpoint.
    @app.middleware("http")
    async def metrics_middleware(
        request: Request, call_next: Callable[[Request], Awaitable[JSONResponse]]
    ) -> JSONResponse:
        start = time.time()
        try:
            response: JSONResponse = await call_next(request)
        except Exception:
            duration = time.time() - start
            record_request(request.method, request.url.path, 500, duration)
            raise
        duration = time.time() - start
        record_request(request.method, request.url.path, response.status_code, duration)
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

    logger.info(
        "JARVIS application created",
        extra={"env": settings.app_env, "version": APP_VERSION},
    )

    return app
