"""Unit tests for JARVIS configuration management."""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from jarvis.core.config import Settings

_TEST_ENV = {
    "JARVIS_APP_SECRET": "test-secret-key-for-unit-tests-only",
    "JARVIS_DATABASE_URL": "postgresql+psycopg://test:test@localhost:5432/testdb",
}


def test_default_settings() -> None:
    """Default settings load with safe values (ignoring local .env)."""
    with patch.dict(os.environ, _TEST_ENV, clear=False):
        s = Settings(_env_file=None)
        assert s.app_name == "jarvis"
        assert s.app_env == "development"
        assert s.debug is False
        assert s.log_level == "info"
        assert s.host == "127.0.0.1"
        assert s.port == 8000
        assert s.workers == 1
        assert s.database_pool_size == 10
        assert s.database_max_overflow == 20
        assert s.access_token_expire_minutes == 30
        assert s.algorithm == "HS256"
        assert s.cloud_fallback_enabled is False
        assert s.default_provider == "local"
        assert s.default_model == "local-model"
        assert s.max_tokens == 4096
        assert s.request_timeout_seconds == 120
        assert s.voice_enabled is False
        assert s.vision_enabled is False
        assert s.agent_runtime_enabled is True
        assert s.smart_environment_enabled is False


def test_env_prefix_loading() -> None:
    """Settings load from JARVIS_ prefixed environment variables."""
    env = {
        **_TEST_ENV,
        "JARVIS_APP_ENV": "production",
        "JARVIS_DEBUG": "true",
        "JARVIS_PORT": "9000",
        "JARVIS_LOG_LEVEL": "debug",
        "JARVIS_CLOUD_FALLBACK_ENABLED": "true",
        "JARVIS_VOICE_ENABLED": "true",
    }
    with patch.dict(os.environ, env, clear=False):
        s = Settings(_env_file=None)
        assert s.app_env == "production"
        assert s.debug is True
        assert s.port == 9000
        assert s.log_level == "debug"
        assert s.app_secret == "test-secret-key-for-unit-tests-only"
        assert s.cloud_fallback_enabled is True
        assert s.voice_enabled is True


def test_secret_key_has_dev_default() -> None:
    """app_secret has a dev default; production requires JARVIS_APP_SECRET."""
    with patch.dict(os.environ, {}, clear=False):
        s = Settings(_env_file=None)
        assert s.app_secret == "dev-secret-change-me-in-production"


def test_secret_key_required_in_production() -> None:
    """Production environment rejects the default secret key."""
    with (
        patch.dict(
            os.environ,
            {"JARVIS_APP_ENV": "production"},
            clear=False,
        ),
        pytest.raises(ValueError),
    ):
        Settings(_env_file=None)


def test_cloud_fallback_disabled_by_default() -> None:
    """Cloud model fallback must be disabled by default per blueprint §4.2."""
    with patch.dict(os.environ, _TEST_ENV, clear=False):
        s = Settings(_env_file=None)
        assert s.cloud_fallback_enabled is False
