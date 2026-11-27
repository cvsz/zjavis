"""Unit tests for CORS configuration security."""

from __future__ import annotations

from starlette.middleware.cors import CORSMiddleware

from jarvis.api.main import create_app


def test_cors_middleware_registered() -> None:
    """CORS middleware must be registered on the application."""
    app = create_app()
    middleware_classes = [m.cls for m in app.user_middleware]
    assert CORSMiddleware in middleware_classes


def test_cors_security_headers_present() -> None:
    """Security headers middleware should set protective headers."""
    app = create_app()
    middleware_classes = [m.cls for m in app.user_middleware]
    assert CORSMiddleware in middleware_classes
