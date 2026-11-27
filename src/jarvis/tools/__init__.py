"""Tool and computer integration adapters.

Per javis-blueprint.md section 9, capability adapters provide typed,
policy-gated access to external systems: file system, terminal, Git,
Docker, browser, and MCP. All adapters enforce:
- Input validation (SSRF, path traversal, command allowlisting)
- Timeout and retry bounds
- Sandboxed, least-privilege execution
- Audit event recording

Adapters are feature-flagged and disabled by default unless explicitly
enabled via configuration, matching the pattern used by voice, vision,
and smart environment services.
"""

from __future__ import annotations

from typing import Any

# Import all capability adapters (importing instantiates the singletons)
from jarvis.tools.browser import browser_tool
from jarvis.tools.docker import docker_tool
from jarvis.tools.file import file_tool
from jarvis.tools.git import git_tool
from jarvis.tools.mcp import mcp_tool
from jarvis.tools.terminal import terminal_tool

# Tool registry: name -> adapter instance
_tool_registry: dict[str, Any] = {}

# Register all adapters
for _adapter in (
    file_tool,
    terminal_tool,
    git_tool,
    docker_tool,
    mcp_tool,
    browser_tool,
):
    _tool_registry[_adapter.provider_name] = _adapter


def register_tool(name: str, adapter: Any) -> None:
    """Register a capability adapter in the tool registry."""
    _tool_registry[name] = adapter


def get_tool(name: str) -> Any | None:
    """Retrieve a registered capability adapter by name."""
    return _tool_registry.get(name)


def list_tools() -> list[str]:
    """Return the names of all registered capability adapters."""
    return sorted(_tool_registry.keys())


__all__ = [
    "browser_tool",
    "docker_tool",
    "file_tool",
    "get_tool",
    "git_tool",
    "list_tools",
    "mcp_tool",
    "register_tool",
    "terminal_tool",
]
