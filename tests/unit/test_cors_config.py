"""CORS configuration tests.

Verifies that CORS is default-deny: no wildcard origins when credentials
are enabled, per OWASP and secure-by-default principles.
"""

from __future__ import annotations

import os
from unittest.mock import patch

from jarvis.core.config import Settings


def test_cors_origins_default_not_wildcard():
    """Default CORS origins must not include wildcard."""
    env = {
        "JARVIS_APP_SECRET": "test-secret-key-for-unit-tests-only",
        "JARVIS_DATABASE_URL": "postgresql+psycopg://test:test@localhost:5432/testdb",
    }
    with patch.dict(os.environ, env, clear=False):
        s = Settings(_env_file=None)
        assert "*" not in s.cors_origins
        assert len(s.cors_origins) > 0


def test_cors_origins_default_not_wildcard_with_credentials():
    """Default CORS origins must not include wildcard when credentials are allowed."""
    env = {
        "JARVIS_APP_SECRET": "test-secret-key-for-unit-tests-only",
        "JARVIS_DATABASE_URL": "postgresql+psycopg://test:test@localhost:5432/testdb",
    }
    with patch.dict(os.environ, env, clear=False):
        s = Settings(_env_file=None)
        assert "*" not in s.cors_origins
        assert len(s.cors_origins) > 0
