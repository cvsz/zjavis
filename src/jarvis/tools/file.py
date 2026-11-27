"""File system capability adapter.

Provides read/write access to files within a configured base directory,
with path traversal prevention via ``validate_safe_path()``. All file
operations are confined to the base directory to prevent directory
escape attacks.
"""

from __future__ import annotations

import asyncio
import os
from typing import Any

from jarvis.core.exceptions import ValidationError
from jarvis.core.logging import get_logger
from jarvis.core.security import validate_safe_path
from jarvis.tools.base import BaseToolAdapter, ToolResult

logger = get_logger(__name__)

# Default base directory for file operations. Override via
# JARVIS_TOOL_FILE_BASE_DIR if needed.
DEFAULT_FILE_BASE_DIR = os.path.abspath(".")


def _read_file(file_path: str) -> str:
    """Read file contents (blocking, intended for asyncio.to_thread)."""
    with open(file_path, "r", encoding="utf-8") as fh:
        return fh.read()


def _write_file(file_path: str, content: str) -> None:
    """Write file contents (blocking, intended for asyncio.to_thread)."""
    with open(file_path, "w", encoding="utf-8") as fh:
        fh.write(content)


class FileToolAdapter(BaseToolAdapter):
    """File system adapter with path-traversal prevention.

    Supports:
    - ``read``: Read file contents within base directory
    - ``write``: Write file contents within base directory
    - ``list``: List directory contents within base directory
    - ``exists``: Check if a path exists within base directory

    All paths are validated against ``base_dir`` using
    ``validate_safe_path()`` to prevent directory escape.
    """

    def __init__(
        self, *, enabled: bool = False, base_dir: str = DEFAULT_FILE_BASE_DIR
    ) -> None:
        super().__init__(provider_name="file", enabled=enabled)
        self.base_dir = base_dir
        if not os.path.isdir(self.base_dir):
            raise ValidationError(
                f"File tool base directory does not exist: {self.base_dir}",
                code="invalid_base_directory",
                details={"base_dir": self.base_dir},
            )

    async def execute(self, *, action: str, params: dict[str, Any]) -> ToolResult:
        """Execute a file system action.

        Args:
            action: One of ``read``, ``write``, ``list``, ``exists``.
            params: Action-specific parameters.

        Returns:
            A :class:`ToolResult` with the operation outcome.
        """
        self._require_enabled()

        try:
            if action == "read":
                return await self._read(params)
            if action == "write":
                return await self._write(params)
            if action == "list":
                return await self._list(params)
            if action == "exists":
                return await self._exists(params)
            return ToolResult(
                success=False,
                error=f"Unknown file action: {action}",
                provider=self.provider_name,
            )
        except ValidationError as exc:
            logger.warning(
                "File tool validation error",
                extra={"action": action, "error": exc.code},
            )
            return ToolResult(
                success=False,
                error=exc.message,
                provider=self.provider_name,
                metadata={"code": exc.code},
            )
        except Exception as exc:  # noqa: BLE001 - tool errors are captured
            logger.error(
                "File tool execution error",
                extra={"action": action, "error": str(exc)},
            )
            return ToolResult(
                success=False,
                error=str(exc),
                provider=self.provider_name,
            )

    async def _read(self, params: dict[str, Any]) -> ToolResult:
        path = params.get("path")
        if not path or not isinstance(path, str):
            return ToolResult(
                success=False,
                error="Missing required parameter: path",
                provider=self.provider_name,
            )
        safe_path = validate_safe_path(self.base_dir, path)
        if not os.path.isfile(safe_path):
            return ToolResult(
                success=False,
                error=f"File not found: {path}",
                provider=self.provider_name,
            )
        try:
            content = await asyncio.to_thread(_read_file, safe_path)
            return ToolResult(
                success=True,
                data={"path": path, "content": content},
                provider=self.provider_name,
            )
        except OSError as exc:
            return ToolResult(
                success=False,
                error=f"Failed to read file: {exc}",
                provider=self.provider_name,
            )

    async def _write(self, params: dict[str, Any]) -> ToolResult:
        path = params.get("path")
        content = params.get("content", "")
        if not path or not isinstance(path, str):
            return ToolResult(
                success=False,
                error="Missing required parameter: path",
                provider=self.provider_name,
            )
        safe_path = validate_safe_path(self.base_dir, path)
        try:
            await asyncio.to_thread(
                lambda: os.makedirs(os.path.dirname(safe_path), exist_ok=True)
            )
            await asyncio.to_thread(_write_file, safe_path, content)
            return ToolResult(
                success=True,
                data={"path": path, "bytes_written": len(content.encode("utf-8"))},
                provider=self.provider_name,
            )
        except OSError as exc:
            return ToolResult(
                success=False,
                error=f"Failed to write file: {exc}",
                provider=self.provider_name,
            )

    async def _list(self, params: dict[str, Any]) -> ToolResult:
        path = params.get("path", ".")
        safe_path = validate_safe_path(self.base_dir, path)
        if not os.path.isdir(safe_path):
            return ToolResult(
                success=False,
                error=f"Directory not found: {path}",
                provider=self.provider_name,
            )
        try:
            entries = []
            for entry in sorted(os.listdir(safe_path)):
                full = os.path.join(safe_path, entry)
                entries.append(
                    {
                        "name": entry,
                        "is_dir": os.path.isdir(full),
                        "path": os.path.relpath(full, self.base_dir),
                    }
                )
            return ToolResult(
                success=True,
                data={"path": path, "entries": entries},
                provider=self.provider_name,
            )
        except OSError as exc:
            return ToolResult(
                success=False,
                error=f"Failed to list directory: {exc}",
                provider=self.provider_name,
            )

    async def _exists(self, params: dict[str, Any]) -> ToolResult:
        path = params.get("path")
        if not path or not isinstance(path, str):
            return ToolResult(
                success=False,
                error="Missing required parameter: path",
                provider=self.provider_name,
            )
        try:
            safe_path = validate_safe_path(self.base_dir, path)
            return ToolResult(
                success=True,
                data={"path": path, "exists": os.path.exists(safe_path)},
                provider=self.provider_name,
            )
        except ValidationError:
            return ToolResult(
                success=True,
                data={"path": path, "exists": False},
                provider=self.provider_name,
            )


file_tool = FileToolAdapter(
    enabled=False,  # Disabled by default; enable via configuration
)

__all__ = [
    "DEFAULT_FILE_BASE_DIR",
    "FileToolAdapter",
    "file_tool",
]
