"""Pytest configuration and shared fixtures for JARVIS integration tests.

Provides synchronous fixtures that drive async code through asyncio.run().
"""

from __future__ import annotations

import pytest

from jarvis.api.main import create_app


def _run(coro):
    """Run an async coroutine in a new event loop."""
    import asyncio

    return asyncio.run(coro)


@pytest.fixture
def app():
    """Provide the FastAPI application instance."""
    return create_app()
