"""Git capability adapter.

Provides read-only Git operations within a configured repository
directory. Only safe, non-destructive Git commands are permitted:
status, log, diff, show, branch, rev-parse, and remote -v.

Write operations (push, commit, merge, reset, checkout, etc.) are
intentionally excluded to prevent accidental repository modification.
"""

from __future__ import annotations

import os
from typing import Any

from jarvis.core.logging import get_logger
from jarvis.core.security import validate_safe_path
from jarvis.tools.base import BaseToolAdapter, ToolResult
from jarvis.tools.terminal import TerminalToolAdapter

# Dedicated (read-only) terminal runner for git operations. It is
# independent of the shared ``terminal_tool`` singleton so that enabling
# the git adapter does not depend on the general terminal adapter being
# enabled, and vice versa.
_git_terminal = TerminalToolAdapter(enabled=True)

logger = get_logger(__name__)

# Read-only Git subcommands permitted through this adapter.
READ_ONLY_GIT_COMMANDS: frozenset[str] = frozenset(
    {
        "status",
        "log",
        "diff",
        "show",
        "branch",
        "rev-parse",
        "remote",
        "show-ref",
        "describe",
        "blame",
    }
)


class GitToolAdapter(BaseToolAdapter):
    """Read-only Git adapter for repository inspection.

    Delegates to the terminal adapter with allowlisted Git commands.
    All operations are confined to a configured repository root using
    path traversal prevention.
    """

    def __init__(
        self,
        *,
        enabled: bool = False,
        repo_root: str | None = None,
    ) -> None:
        super().__init__(provider_name="git", enabled=enabled)
        self.repo_root = repo_root or os.getcwd()

    async def execute(self, *, action: str, params: dict[str, Any]) -> ToolResult:
        """Execute a Git action.

        Args:
            action: One of ``run``.
            params: Must include ``args`` (list of Git subcommand args).

        Returns:
            A :class:`ToolResult`` with the Git command output.
        """
        self._require_enabled()

        if action != "run":
            return ToolResult(
                success=False,
                error=f"Unknown git action: {action}",
                provider=self.provider_name,
            )

        args = params.get("args")
        if not args or not isinstance(args, list):
            return ToolResult(
                success=False,
                error="Missing required parameter: args (list of strings)",
                provider=self.provider_name,
            )

        git_command = ["git"] + args
        subcommand = args[0] if args else ""

        # Allow global flags (e.g. --version, --help) and read-only subcommands.
        if subcommand.startswith("-"):
            # Global flags are safe read-only operations
            pass
        elif subcommand not in READ_ONLY_GIT_COMMANDS:
            return ToolResult(
                success=False,
                error=f"Git subcommand not permitted (read-only adapter): {subcommand}",
                provider=self.provider_name,
                metadata={
                    "permitted": sorted(READ_ONLY_GIT_COMMANDS),
                },
            )

        # Validate repo_root is a safe directory
        try:
            validate_safe_path(self.repo_root, ".")
        except Exception as exc:  # noqa: BLE001
            return ToolResult(
                success=False,
                error=f"Invalid repository root: {exc}",
                provider=self.provider_name,
            )

        result = await _git_terminal.execute(
            action="run",
            params={
                "command": git_command,
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


git_tool = GitToolAdapter(
    enabled=False,  # Disabled by default; enable via configuration
)

__all__ = [
    "READ_ONLY_GIT_COMMANDS",
    "GitToolAdapter",
    "git_tool",
]
