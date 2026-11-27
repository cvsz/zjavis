"""Engineering intelligence capabilities.

Per javis-blueprint.md section 10, engineering intelligence provides
repository discovery, architecture analysis, code review assistance,
test execution, security scanning, documentation workflows, and
release readiness assessment.

All operations are read-only and governed by the policy engine.
No repository mutations are performed by this package.
"""

from __future__ import annotations

from typing import Any

# Engineering intelligence registry: name -> capability instance
_engineering_registry: dict[str, Any] = {}


def register_capability(name: str, capability: Any) -> None:
    """Register an engineering intelligence capability."""
    _engineering_registry[name] = capability


def get_capability(name: str) -> Any | None:
    """Retrieve a registered engineering capability by name."""
    return _engineering_registry.get(name)


def list_capabilities() -> list[str]:
    """Return the names of all registered engineering capabilities."""
    return sorted(_engineering_registry.keys())


__all__ = [
    "get_capability",
    "list_capabilities",
    "register_capability",
]
