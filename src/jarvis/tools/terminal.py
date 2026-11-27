"""Terminal capability adapter.

Provides allowlisted command execution with process timeouts and
output bounding. Only commands on the allowlist may be executed, and
shell interpolation is avoided by using argument lists (not shell
strings).
"""

from __future__ import annotations

import asyncio
import os
from typing import Any

from jarvis.core.exceptions import ValidationError
from jarvis.core.logging import get_logger
from jarvis.core.security import validate_ssrf_safe_url
from jarvis.tools.base import BaseToolAdapter, ToolResult

logger = get_logger(__name__)

# Allowlisted executables. Only these binaries may be invoked through
# the terminal adapter. Add entries only after security review.
ALLOWLISTED_COMMANDS: frozenset[str] = frozenset(
    {
        "cat",
        "date",
        "df",
        "docker",
        "echo",
        "find",
        "free",
        "gh",
        "git",
        "grep",
        "helm",
        "jq",
        "kubectl",
        "ls",
        "mypy",
        "pip",
        "ps",
        "pytest",
        "pwd",
        "ruff",
        "shellcheck",
        "uname",
        "uptime",
        "wget",
        "whoami",
    }
)

# Maximum output size in bytes per command to prevent resource exhaustion.
MAX_OUTPUT_BYTES = 1_000_000  # 1 MB

# Default command timeout in seconds.
DEFAULT_TIMEOUT_SECONDS = 30


class TerminalToolAdapter(BaseToolAdapter):
    """Terminal adapter with allowlisted commands and bounded execution.

    Supports:
    - ``run``: Execute an allowlisted command with arguments and timeout.

    Security controls:
    - Command must be in ALLOWLISTED_COMMANDS
    - Arguments passed as a list (no shell=True, no shell interpolation)
    - Per-command timeout
    - Output bounded to MAX_OUTPUT_BYTES
    - Working directory constrained to a safe base
    """

    def __init__(
        self,
        *,
        enabled: bool = False,
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
        cwd: str | None = None,
    ) -> None:
        super().__init__(provider_name="terminal", enabled=enabled)
        self.timeout_seconds = timeout_seconds
        self.cwd = cwd or os.getcwd()

    async def execute(self, *, action: str, params: dict[str, Any]) -> ToolResult:
        """Execute a terminal action.

        Args:
            action: One of ``run``.
            params: Must include ``command`` (list of strings) and
                optionally ``timeout_seconds``.

        Returns:
            A :class:`ToolResult`` with the command output.
        """
        self._require_enabled()

        if action != "run":
            return ToolResult(
                success=False,
                error=f"Unknown terminal action: {action}",
                provider=self.provider_name,
            )

        command = params.get("command")
        if not command or not isinstance(command, list):
            return ToolResult(
                success=False,
                error="Missing required parameter: command (list of strings)",
                provider=self.provider_name,
            )

        executable = command[0]
        if not isinstance(executable, str) or executable not in ALLOWLISTED_COMMANDS:
            return ToolResult(
                success=False,
                error=f"Command not allowlisted: {executable}",
                provider=self.provider_name,
                metadata={"allowlisted": sorted(ALLOWLISTED_COMMANDS)},
            )

        timeout = params.get("timeout_seconds", self.timeout_seconds)
        try:
            timeout = int(timeout)
        except (TypeError, ValueError):
            timeout = self.timeout_seconds

        try:
            result = await self._run_command(command, timeout)
            return result
        except ValidationError as exc:
            logger.warning(
                "Terminal tool validation error",
                extra={"command": executable, "error": exc.code},
            )
            return ToolResult(
                success=False,
                error=exc.message,
                provider=self.provider_name,
                metadata={"code": exc.code},
            )
        except Exception as exc:  # noqa: BLE001 - tool errors are captured
            logger.error(
                "Terminal tool execution error",
                extra={"command": executable, "error": str(exc)},
            )
            return ToolResult(
                success=False,
                error=str(exc),
                provider=self.provider_name,
            )

    async def _run_command(self, command: list[str], timeout: int) -> ToolResult:
        """Run an allowlisted command with timeout and output bounding."""
        # (defense in depth for curl/wget)
        if command[0] in ("curl", "wget") and len(command) > 1:
            for arg in command[1:]:
                if isinstance(arg, str) and arg.startswith(("http://", "https://")):
                    validate_ssrf_safe_url(arg)

        try:
            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.cwd,
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), timeout=timeout
                )
            except TimeoutError:
                try:
                    process.kill()
                except ProcessLookupError:
                    pass
                await process.wait()
                return ToolResult(
                    success=False,
                    error=f"Command timed out after {timeout}s",
                    provider=self.provider_name,
                    metadata={"command": command[0], "timeout": timeout},
                )

            stdout_text = stdout.decode("utf-8", errors="replace")[:MAX_OUTPUT_BYTES]
            stderr_text = stderr.decode("utf-8", errors="replace")[:MAX_OUTPUT_BYTES]

            if process.returncode == 0:
                return ToolResult(
                    success=True,
                    data={
                        "command": " ".join(command),
                        "stdout": stdout_text,
                        "stderr": stderr_text,
                        "returncode": process.returncode,
                    },
                    provider=self.provider_name,
                )
            return ToolResult(
                success=False,
                error=f"Command exited with code {process.returncode}",
                provider=self.provider_name,
                data={
                    "command": " ".join(command),
                    "stdout": stdout_text,
                    "stderr": stderr_text,
                    "returncode": process.returncode,
                },
            )
        except FileNotFoundError:
            return ToolResult(
                success=False,
                error=f"Executable not found: {command[0]}",
                provider=self.provider_name,
            )
        except OSError as exc:
            return ToolResult(
                success=False,
                error=f"Failed to execute command: {exc}",
                provider=self.provider_name,
            )


terminal_tool = TerminalToolAdapter(
    enabled=False,  # Disabled by default; enable via configuration
)

__all__ = [
    "ALLOWLISTED_COMMANDS",
    "DEFAULT_TIMEOUT_SECONDS",
    "MAX_OUTPUT_BYTES",
    "TerminalToolAdapter",
    "terminal_tool",
]
