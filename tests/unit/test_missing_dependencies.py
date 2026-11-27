"""Missing dependency tests.

Verifies that all production and development dependencies required by the
JARVIS application are importable in the current environment. A missing
dependency must fail this test suite so it is caught before deployment
rather than at runtime.
"""

from __future__ import annotations

import importlib

import pytest

# Production dependencies that must be importable for the application to run.
PRODUCTION_DEPENDENCIES = [
    "fastapi",
    "uvicorn",
    "pydantic",
    "pydantic_settings",
    "starlette",
    "sqlalchemy",
    "psycopg",
    "alembic",
    "prometheus_client",
    "httpx",
]

# Development / tooling dependencies that must be importable for CI/CD.
DEV_DEPENDENCIES = [
    "pytest",
    "ruff",
    "mypy",
    "bandit",
]


class TestMissingDependencies:
    """Tests that verify required dependencies are installed and importable."""

    @pytest.mark.parametrize("module_name", PRODUCTION_DEPENDENCIES)
    def test_production_dependency_importable(self, module_name: str) -> None:
        """Each production dependency must be importable."""
        try:
            importlib.import_module(module_name)
        except ImportError as exc:
            pytest.fail(f"Missing production dependency: {module_name} ({exc})")

    @pytest.mark.parametrize("module_name", DEV_DEPENDENCIES)
    def test_dev_dependency_importable(self, module_name: str) -> None:
        """Each development dependency must be importable."""
        try:
            importlib.import_module(module_name)
        except ImportError as exc:
            pytest.fail(f"Missing development dependency: {module_name} ({exc})")

    def test_jarvis_package_importable(self) -> None:
        """The jarvis application package must be importable."""
        try:
            importlib.import_module("jarvis")
        except ImportError as exc:
            pytest.fail(f"jarvis package not importable: {exc}")

    def test_jarvis_subpackages_importable(self) -> None:
        """All jarvis subpackages must be importable."""
        subpackages = [
            "jarvis.api",
            "jarvis.auth",
            "jarvis.core",
            "jarvis.db",
            "jarvis.ai",
            "jarvis.approval",
            "jarvis.audit",
            "jarvis.orchestration",
            "jarvis.policy",
        ]
        for module_name in subpackages:
            try:
                importlib.import_module(module_name)
            except ImportError as exc:
                pytest.fail(f"Missing jarvis subpackage: {module_name} ({exc})")

    def test_jarvis_modules_importable(self) -> None:
        """Key jarvis modules must be importable."""
        modules = [
            "jarvis.api.main",
            "jarvis.api.auth",
            "jarvis.api.conversations",
            "jarvis.api.memory",
            "jarvis.api.approvals",
            "jarvis.api.audit",
            "jarvis.api.agents",
            "jarvis.api.tasks",
            "jarvis.api.agent_runtime",
            "jarvis.api.voice",
            "jarvis.api.vision",
            "jarvis.api.smart_environment",
            "jarvis.api.health",
            "jarvis.core.config",
            "jarvis.core.security",
            "jarvis.core.policy",
            "jarvis.core.logging",
            "jarvis.core.metrics",
            "jarvis.core.exceptions",
            "jarvis.db.session",
            "jarvis.db.models",
            "jarvis.ai.gateway",
            "jarvis.ai.provider",
            "jarvis.ai.context",
            "jarvis.ai.memory",
            "jarvis.ai.agent_runtime",
            "jarvis.ai.voice",
            "jarvis.ai.vision",
            "jarvis.ai.smart_environment",
            "jarvis.orchestration",
            "jarvis.approval",
            "jarvis.audit",
            "jarvis.policy",
        ]
        for module_name in modules:
            try:
                importlib.import_module(module_name)
            except ImportError as exc:
                pytest.fail(f"Missing jarvis module: {module_name} ({exc})")
