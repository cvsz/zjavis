"""Docker capability adapter.

Provides read-only Docker inspection operations. Only inspect-type
commands are permitted; container lifecycle operations (start, stop,
run, rm, build, push) are intentionally excluded.
"""

from __future__ import annotations

from typing import Any

from jarvis.core.logging import get_logger
from jarvis.tools.base import BaseToolAdapter, ToolResult
from jarvis.tools.terminal import TerminalToolAdapter

# Dedicated (read-only) terminal runner for Docker operations. It is
# independent of the shared ``terminal_tool`` singleton so that enabling
# the Docker adapter does not depend on the general terminal adapter
# being enabled, and vice versa.
_docker_terminal = TerminalToolAdapter(enabled=True)

logger = get_logger(__name__)

# Read-only Docker subcommands permitted through this adapter.
READ_ONLY_DOCKER_COMMANDS: frozenset[str] = frozenset(
    {
        "ps",
        "images",
        "inspect",
        "version",
        "info",
        "stats",
        "top",
        "logs",
        "events",
    }
)


class DockerToolAdapter(BaseToolAdapter):
    """Read-only Docker adapter for container inspection.

    Delegates to the terminal adapter with allowlisted Docker commands.
    No container lifecycle mutations are permitted.
    """

    def __init__(self, *, enabled: bool = False) -> None:
        super().__init__(provider_name="docker", enabled=enabled)

    async def execute(self, *, action: str, params: dict[str, Any]) -> ToolResult:
        """Execute a Docker action.

        Args:
            action: One of ``run``.
            params: Must include ``args`` (list of Docker subcommand args).

        Returns:
            A :class:`ToolResult`` with the Docker command output.
        """
        self._require_enabled()

        if action != "run":
            return ToolResult(
                success=False,
                error=f"Unknown docker action: {action}",
                provider=self.provider_name,
            )

        args = params.get("args")
        if not args or not isinstance(args, list):
            return ToolResult(
                success=False,
                error="Missing required parameter: args (list of strings)",
                provider=self.provider_name,
            )

        subcommand = args[0] if args else ""

        if subcommand not in READ_ONLY_DOCKER_COMMANDS:
            return ToolResult(
                success=False,
                error=f"Docker subcommand not permitted (read-only adapter): {subcommand}",
                provider=self.provider_name,
                metadata={
                    "permitted": sorted(READ_ONLY_DOCKER_COMMANDS),
                },
            )

        docker_command = ["docker"] + args

        result = await _docker_terminal.execute(
            action="run",
            params={
                "command": docker_command,
                "timeout_seconds": 30,
            },
        )
        return ToolResult(
            success=result.success,
            data=result.data,
            error=result.error,
            provider=self.provider_name,
            metadata=result.metadata,
        )


docker_tool = DockerToolAdapter(
    enabled=False,  # Disabled by default; enable via configuration
)

__all__ = [
    "READ_ONLY_DOCKER_COMMANDS",
    "DockerToolAdapter",
    "docker_tool",
]
