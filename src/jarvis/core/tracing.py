"""Distributed tracing via OpenTelemetry.

Provides a tracer provider and helper functions for emitting spans across
API requests, model gateway calls, agent executions, tool calls, and
database operations. Traces are exported to an OpenTelemetry collector
when configured; otherwise a no-op tracer is used so the application
remains functional without observability infrastructure.

Per javis-blueprint.md section 17.2, trace and correlation identifiers
are propagated across API requests, model calls, agent executions, tool
calls, events, database operations, and approval workflows. Secrets,
raw credentials, and unnecessary private content are never recorded in
telemetry.
"""

from __future__ import annotations

from typing import Any, Self

from jarvis.core.config import settings
from jarvis.core.logging import get_logger

logger = get_logger(__name__)

# Lazily initialized tracer provider
_tracer_provider: Any = None
_tracer: Any = None
_tracing_initialized: bool = False


def _is_tracing_enabled() -> bool:
    """Return True if OpenTelemetry tracing is explicitly enabled."""
    return bool(settings.tracing_enabled)


def _init_tracer() -> Any:
    """Initialize the OpenTelemetry tracer if available and enabled.

    Returns a tracer instance (no-op if OpenTelemetry is not installed
    or tracing is disabled). Never raises: failure to initialize tracing
    must not prevent the application from starting.
    """
    global _tracer_provider, _tracer, _tracing_initialized

    if _tracing_initialized:
        return _tracer

    _tracing_initialized = True

    if not _is_tracing_enabled():
        logger.info(
            "OpenTelemetry tracing disabled (set JARVIS_TRACING_ENABLED=true to enable)"
        )
        _tracer = _NoopTracer()
        return _tracer

    try:
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import (
            ConsoleSpanExporter,
            SimpleSpanProcessor,
        )

        _tracer_provider = TracerProvider()
        # Export to console by default; configure an OTLP exporter via
        # JARVIS_OTLP_ENDPOINT for production use.
        otlp_endpoint = settings.otlp_endpoint
        exporter: Any
        if otlp_endpoint:
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
                OTLPSpanExporter,
            )

            exporter = OTLPSpanExporter(endpoint=otlp_endpoint)
        else:
            exporter = ConsoleSpanExporter()

        _tracer_provider.add_span_processor(SimpleSpanProcessor(exporter))
        trace.set_tracer_provider(_tracer_provider)
        _tracer = trace.get_tracer("jarvis", "0.1.0")
        logger.info("OpenTelemetry tracing initialized")
    except ImportError:
        logger.warning(
            "OpenTelemetry not installed; tracing disabled. "
            "Install opentelemetry-sdk and opentelemetry-exporter-otlp to enable."
        )
        _tracer = _NoopTracer()
    except Exception as exc:  # noqa: BLE001 - tracing must not break startup
        logger.warning(
            "Failed to initialize OpenTelemetry tracing",
            extra={"error": str(exc)},
        )
        _tracer = _NoopTracer()

    return _tracer


def get_tracer() -> Any:
    """Return the OpenTelemetry tracer, initializing it on first call.

    The returned object supports ``start_as_current_span(name)`` as a
    context manager. If tracing is unavailable, a no-op tracer is
    returned so callers can use the same API without conditional logic.
    """
    if _tracer is None:
        _init_tracer()
    return _tracer or _NoopTracer()


def start_span(name: str, attributes: dict[str, Any] | None = None) -> Any:
    """Start a new trace span with optional attributes.

    Secrets and private data must never be included in attributes.
    """
    tracer = get_tracer()
    span = tracer.start_span(name)
    if attributes:
        for key, value in attributes.items():
            # Never record secret-like keys
            if _is_secret_key(key):
                continue
            try:
                span.set_attribute(key, str(value))
            except Exception:  # noqa: BLE001 - best effort
                logger.debug(
                    "Failed to set trace attribute",
                    extra={"key": key},
                )
    return span


def _is_secret_key(key: str) -> bool:
    """Return True if a telemetry attribute key looks secret-like."""
    secret_keys = (
        "password",
        "passwd",
        "secret",
        "token",
        "api_key",
        "apikey",
        "authorization",
        "credential",
        "private_key",
        "session",
        "cookie",
        "jwt",
        "refresh_token",
        "access_token",
    )
    lower = key.lower()
    return any(s in lower for s in secret_keys)


class _NoopSpan:
    """A no-op span that supports the context manager protocol."""

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def set_attribute(self, key: str, value: Any) -> None:
        return None

    def set_status(self, *args: object, **kwargs: object) -> None:
        return None

    def end(self) -> None:
        return None


class _NoopTracer:
    """A no-op tracer used when OpenTelemetry is unavailable or disabled."""

    def start_span(self, name: str, *args: object, **kwargs: object) -> _NoopSpan:
        return _NoopSpan()

    def start_as_current_span(
        self, name: str, *args: object, **kwargs: object
    ) -> _NoopSpan:
        return _NoopSpan()


tracer = get_tracer()

__all__ = [
    "get_tracer",
    "is_tracing_initialized",
    "start_span",
    "tracer",
]


def is_tracing_initialized() -> bool:
    """Return True if the tracer has been initialized."""
    return _tracing_initialized
