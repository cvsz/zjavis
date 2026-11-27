"""OpenTelemetry tracing export tests.

Verifies that tracing can be enabled with an OTLP HTTP endpoint and that
spans are exported to a local collector. Tracing is no-op when disabled
or when OpenTelemetry is not installed.
"""

from __future__ import annotations

import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import ClassVar
from unittest import mock

from jarvis.core import tracing


class _OTLPHandler(BaseHTTPRequestHandler):
    """Minimal OTLP HTTP trace export endpoint for tests."""

    exports: ClassVar[list[bytes]] = []

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        _OTLPHandler.exports.append(body)
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"")

    def log_message(self, fmt: str, *args: object) -> None:
        """Silence request logging."""


def _start_otlp_server() -> tuple[HTTPServer, int]:
    server = HTTPServer(("127.0.0.1", 0), _OTLPHandler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, port


def _reset_tracing() -> None:
    """Reset module-level tracing state for re-initialization."""
    tracing._tracer_provider = None
    tracing._tracer = None
    tracing._tracing_initialized = False


def test_tracing_disabled_by_default() -> None:
    """Tracing is a no-op tracer when disabled."""
    _reset_tracing()
    with mock.patch.object(tracing.settings, "tracing_enabled", False):
        tracer = tracing.get_tracer()
        span = tracer.start_span("test-span")
        assert isinstance(span, tracing._NoopSpan)


def test_tracing_enabled_uses_otlp_endpoint() -> None:
    """When enabled with an OTLP endpoint, spans are exported to the collector."""
    _OTLPHandler.exports.clear()
    server, port = _start_otlp_server()
    try:
        endpoint = f"http://127.0.0.1:{port}/v1/traces"
        _reset_tracing()
        with (
            mock.patch.object(tracing.settings, "tracing_enabled", True),
            mock.patch.object(tracing.settings, "otlp_endpoint", endpoint),
        ):
            tracer = tracing.get_tracer()
            assert not isinstance(tracer, tracing._NoopTracer)
            with tracer.start_as_current_span("test-operation") as span:
                span.set_attribute("jarvis.operation", "test")

            # Flush: SimpleSpanProcessor exports on end, but give the
            # exporter a moment to send the HTTP request.
            import time

            time.sleep(0.5)

        assert len(_OTLPHandler.exports) >= 1, (
            "Expected at least one OTLP export request"
        )
        # The exported body should be non-empty protobuf payload.
        assert len(_OTLPHandler.exports[0]) > 0
    finally:
        server.shutdown()


def test_tracing_enabled_without_endpoint_returns_real_tracer() -> None:
    """When enabled without an OTLP endpoint, a real tracer (not no-op) is used."""
    _reset_tracing()
    with (
        mock.patch.object(tracing.settings, "tracing_enabled", True),
        mock.patch.object(tracing.settings, "otlp_endpoint", None),
    ):
        tracer = tracing.get_tracer()
        assert not isinstance(tracer, tracing._NoopTracer)


def test_start_span_redacts_secret_keys() -> None:
    """Secret-like attribute keys are never recorded in trace attributes."""
    _reset_tracing()
    with (
        mock.patch.object(tracing.settings, "tracing_enabled", True),
        mock.patch.object(tracing.settings, "otlp_endpoint", None),
    ):
        tracing.get_tracer()
        # Verify _is_secret_key behavior directly.
        assert tracing._is_secret_key("api_key") is True
        assert tracing._is_secret_key("authorization") is True
        assert tracing._is_secret_key("password") is True
        assert tracing._is_secret_key("session") is True
        assert tracing._is_secret_key("normal_attribute") is False
        assert tracing._is_secret_key("jarvis.operation") is False


def test_tracing_returns_noop_when_disabled_even_if_opentelemetry_installed() -> None:
    """Tracing returns a no-op tracer when disabled, regardless of installation."""
    _reset_tracing()
    with mock.patch.object(tracing.settings, "tracing_enabled", False):
        tracer = tracing.get_tracer()
        assert isinstance(tracer, tracing._NoopTracer)


def test_get_tracer_caches_instance() -> None:
    """get_tracer() returns the same instance after initialization."""
    _reset_tracing()
    with mock.patch.object(tracing.settings, "tracing_enabled", False):
        first = tracing.get_tracer()
        second = tracing.get_tracer()
        assert first is second
