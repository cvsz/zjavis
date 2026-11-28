"""Unit tests for the JARVIS tool adapters (Phase 7 capability adapters).

Tests cover:
- File tool adapter (read, write, list, exists with path traversal prevention)
- Terminal tool adapter (allowlisted commands, timeout)
- Git tool adapter (read-only operations)
- Docker tool adapter (read-only operations)
- MCP tool adapter (SSRF validation)
- Browser tool adapter (SSRF prevention)
- Tool registry (register, get, list)
"""

from __future__ import annotations

import os
import tempfile
from collections.abc import Generator
from typing import Any
from unittest.mock import MagicMock

import pytest

from jarvis.tools import get_tool, list_tools, register_tool
from jarvis.tools.base import BaseToolAdapter, ToolResult
from jarvis.tools.browser import BrowserToolAdapter
from jarvis.tools.docker import DockerToolAdapter
from jarvis.tools.file import (
    FileToolAdapter,
)
from jarvis.tools.git import GitToolAdapter
from jarvis.tools.mcp import MCPToolAdapter
from jarvis.tools.terminal import (
    ALLOWLISTED_COMMANDS,
    DEFAULT_TIMEOUT_SECONDS,
    MAX_OUTPUT_BYTES,
    TerminalToolAdapter,
)

# ---------------------------------------------------------------------------
# ToolResult tests
# ---------------------------------------------------------------------------


class TestToolResult:
    """Tests for ToolResult."""

    def test_tool_result_success(self) -> None:
        result = ToolResult(success=True, data={"key": "value"}, provider="test")
        assert result.success is True
        assert result.data == {"key": "value"}
        assert result.error is None
        assert result.provider == "test"
        d = result.to_dict()
        assert d["success"] is True
        assert d["data"] == {"key": "value"}
        assert d["error"] is None
        assert d["provider"] == "test"

    def test_tool_result_failure(self) -> None:
        result = ToolResult(success=False, error="something failed", provider="test")
        assert result.success is False
        assert result.error == "something failed"
        d = result.to_dict()
        assert d["success"] is False


# ---------------------------------------------------------------------------
# BaseToolAdapter tests
# ---------------------------------------------------------------------------


class _ConcreteAdapter(BaseToolAdapter):
    """Concrete test adapter."""

    def __init__(self, *, provider_name: str = "test", enabled: bool = True) -> None:
        super().__init__(provider_name=provider_name, enabled=enabled)

    async def execute(self, *, action: str, params: dict[str, Any]) -> ToolResult:
        return ToolResult(success=True, data={"action": action}, provider="test")


class TestBaseToolAdapter:
    """Tests for BaseToolAdapter."""

    def test_adapter_disabled_raises(self) -> None:
        adapter = _ConcreteAdapter(enabled=False)
        with pytest.raises(RuntimeError, match="is disabled"):
            adapter._require_enabled()

    def test_adapter_enabled(self) -> None:
        adapter = _ConcreteAdapter(enabled=True)
        adapter._require_enabled()  # should not raise

    def test_api_name(self) -> None:
        adapter = _ConcreteAdapter(provider_name="test-provider")
        assert adapter.api_name == "test-provider"


# ---------------------------------------------------------------------------
# FileToolAdapter tests
# ---------------------------------------------------------------------------


class TestFileToolAdapter:
    """Tests for FileToolAdapter."""

    @pytest.fixture
    def tmp_dir(self) -> Generator[str, None, None]:
        with tempfile.TemporaryDirectory() as tmp:
            yield tmp

    @pytest.fixture
    def adapter(self, tmp_dir: str) -> FileToolAdapter:
        return FileToolAdapter(enabled=True, base_dir=tmp_dir)

    @pytest.mark.asyncio
    async def test_read_file(self, adapter: FileToolAdapter, tmp_dir: str) -> None:
        test_file = os.path.join(tmp_dir, "hello.txt")
        with open(test_file, "w") as fh:  # noqa: ASYNC230 - test setup
            fh.write("hello world")
        result = await adapter.execute(action="read", params={"path": "hello.txt"})
        assert result.success is True
        assert result.data["content"] == "hello world"

    @pytest.mark.asyncio
    async def test_read_nonexistent_file(self, adapter: FileToolAdapter) -> None:
        result = await adapter.execute(
            action="read", params={"path": "nonexistent.txt"}
        )
        assert result.success is False
        assert "File not found" in result.error

    @pytest.mark.asyncio
    async def test_write_file(self, adapter: FileToolAdapter, tmp_dir: str) -> None:
        result = await adapter.execute(
            action="write",
            params={"path": "newfile.txt", "content": "test content"},
        )
        assert result.success is True
        assert result.data["bytes_written"] > 0
        # Verify file was actually written
        with open(os.path.join(tmp_dir, "newfile.txt")) as fh:  # noqa: ASYNC230 - test setup
            assert fh.read() == "test content"

    @pytest.mark.asyncio
    async def test_path_traversal_blocked(self, adapter: FileToolAdapter) -> None:
        result = await adapter.execute(
            action="read", params={"path": "../../../etc/passwd"}
        )
        assert result.success is False
        assert result.error is not None

    @pytest.mark.asyncio
    async def test_null_byte_blocked(self, adapter: FileToolAdapter) -> None:
        result = await adapter.execute(action="read", params={"path": "file\x00.txt"})
        assert result.success is False

    @pytest.mark.asyncio
    async def test_list_directory(self, adapter: FileToolAdapter, tmp_dir: str) -> None:
        os.makedirs(os.path.join(tmp_dir, "subdir"), exist_ok=True)
        with open(os.path.join(tmp_dir, "a.txt"), "w") as fh:  # noqa: ASYNC230 - test setup
            fh.write("a")
        result = await adapter.execute(action="list", params={"path": "."})
        assert result.success is True
        names = [e["name"] for e in result.data["entries"]]
        assert "a.txt" in names
        assert "subdir" in names

    @pytest.mark.asyncio
    async def test_exists(self, adapter: FileToolAdapter, tmp_dir: str) -> None:
        with open(os.path.join(tmp_dir, "exists.txt"), "w") as fh:  # noqa: ASYNC230 - test setup
            fh.write("x")
        result = await adapter.execute(action="exists", params={"path": "exists.txt"})
        assert result.success is True
        assert result.data["exists"] is True

        result = await adapter.execute(action="exists", params={"path": "nope.txt"})
        assert result.success is True
        assert result.data["exists"] is False

    @pytest.mark.asyncio
    async def test_unknown_action(self, adapter: FileToolAdapter) -> None:
        result = await adapter.execute(action="unknown", params={})
        assert result.success is False
        assert "Unknown file action" in result.error

    @pytest.mark.asyncio
    async def test_disabled_adapter(self) -> None:
        disabled = FileToolAdapter(enabled=False)
        with pytest.raises(RuntimeError, match="is disabled"):
            await disabled.execute(action="read", params={"path": "x.txt"})


# ---------------------------------------------------------------------------
# TerminalToolAdapter tests
# ---------------------------------------------------------------------------


class TestTerminalToolAdapter:
    """Tests for TerminalToolAdapter."""

    @pytest.fixture
    def adapter(self) -> TerminalToolAdapter:
        return TerminalToolAdapter(enabled=True)

    @pytest.mark.asyncio
    async def test_allowlisted_command(self, adapter: TerminalToolAdapter) -> None:
        result = await adapter.execute(
            action="run",
            params={"command": ["echo", "hello"]},
        )
        assert result.success is True
        assert "hello" in result.data["stdout"]

    @pytest.mark.asyncio
    async def test_command_not_allowlisted(self, adapter: TerminalToolAdapter) -> None:
        result = await adapter.execute(
            action="run",
            params={"command": ["rm", "-rf", "/"]},
        )
        assert result.success is False
        assert "not allowlisted" in result.error

    @pytest.mark.asyncio
    async def test_unknown_action(self, adapter: TerminalToolAdapter) -> None:
        result = await adapter.execute(action="unknown", params={})
        assert result.success is False

    @pytest.mark.asyncio
    async def test_disabled_adapter(self) -> None:
        disabled = TerminalToolAdapter(enabled=False)
        with pytest.raises(RuntimeError, match="is disabled"):
            await disabled.execute(action="run", params={"command": ["echo", "x"]})

    def test_allowlist_contains_expected(self) -> None:
        assert "echo" in ALLOWLISTED_COMMANDS
        assert "git" in ALLOWLISTED_COMMANDS
        assert "rm" not in ALLOWLISTED_COMMANDS

    def test_defaults(self) -> None:
        assert DEFAULT_TIMEOUT_SECONDS == 30
        assert MAX_OUTPUT_BYTES == 1_000_000


# ---------------------------------------------------------------------------
# GitToolAdapter tests
# ---------------------------------------------------------------------------


class TestGitToolAdapter:
    """Tests for GitToolAdapter."""

    @pytest.fixture
    def adapter(self) -> GitToolAdapter:
        return GitToolAdapter(enabled=True, repo_root=tempfile.gettempdir())

    @pytest.mark.asyncio
    async def test_read_only_git_command(self, adapter: GitToolAdapter) -> None:
        # git --version should work in any environment
        result = await adapter.execute(
            action="run",
            params={"args": ["--version"]},
        )
        # git may or may not be installed; just check it doesn't crash
        assert result.success is True or "not found" in (result.error or "")

    @pytest.mark.asyncio
    async def test_non_readonly_command_blocked(self, adapter: GitToolAdapter) -> None:
        result = await adapter.execute(
            action="run",
            params={"args": ["commit", "-m", "test"]},
        )
        assert result.success is False
        assert "not permitted" in result.error

    @pytest.mark.asyncio
    async def test_disabled_adapter(self) -> None:
        disabled = GitToolAdapter(enabled=False)
        with pytest.raises(RuntimeError, match="is disabled"):
            await disabled.execute(action="run", params={"args": ["status"]})


# ---------------------------------------------------------------------------
# DockerToolAdapter tests
# ---------------------------------------------------------------------------


class TestDockerToolAdapter:
    """Tests for DockerToolAdapter."""

    @pytest.fixture
    def adapter(self) -> DockerToolAdapter:
        return DockerToolAdapter(enabled=True)

    @pytest.mark.asyncio
    async def test_readonly_docker_command(self, adapter: DockerToolAdapter) -> None:
        # docker version should work if docker is installed
        result = await adapter.execute(
            action="run",
            params={"args": ["version"]},
        )
        assert result.success is True or "not found" in (result.error or "")

    @pytest.mark.asyncio
    async def test_non_readonly_command_blocked(
        self, adapter: DockerToolAdapter
    ) -> None:
        result = await adapter.execute(
            action="run",
            params={"args": ["run", "hello-world"]},
        )
        assert result.success is False
        assert "not permitted" in result.error

    @pytest.mark.asyncio
    async def test_disabled_adapter(self) -> None:
        disabled = DockerToolAdapter(enabled=False)
        with pytest.raises(RuntimeError, match="is disabled"):
            await disabled.execute(action="run", params={"args": ["ps"]})


# ---------------------------------------------------------------------------
# MCPToolAdapter tests
# ---------------------------------------------------------------------------


class TestMCPToolAdapter:
    """Tests for MCPToolAdapter."""

    @pytest.fixture
    def adapter(self) -> MCPToolAdapter:
        return MCPToolAdapter(enabled=True)

    @pytest.mark.asyncio
    async def test_ssrf_private_url_blocked(self, adapter: MCPToolAdapter) -> None:
        result = await adapter.execute(
            action="list_tools",
            params={"server_url": "http://10.0.0.1/mcp"},
        )
        assert result.success is False
        assert "security policy" in result.error or "rejected" in result.error

    @pytest.mark.asyncio
    async def test_unsafe_scheme_blocked(self, adapter: MCPToolAdapter) -> None:
        result = await adapter.execute(
            action="list_tools",
            params={"server_url": "ftp://example.com/mcp"},
        )
        assert result.success is False

    @pytest.mark.asyncio
    async def test_missing_server_url(self, adapter: MCPToolAdapter) -> None:
        result = await adapter.execute(action="list_tools", params={})
        assert result.success is False
        assert "server_url" in result.error

    @pytest.mark.asyncio
    async def test_unknown_action(self, adapter: MCPToolAdapter) -> None:
        result = await adapter.execute(action="unknown", params={"server_url": "x"})
        assert result.success is False

    @pytest.mark.asyncio
    async def test_disabled_adapter(self) -> None:
        disabled = MCPToolAdapter(enabled=False)
        with pytest.raises(RuntimeError, match="is disabled"):
            await disabled.execute(
                action="list_tools", params={"server_url": "https://example.com"}
            )


# ---------------------------------------------------------------------------
# BrowserToolAdapter tests
# ---------------------------------------------------------------------------


class TestBrowserToolAdapter:
    """Tests for BrowserToolAdapter."""

    @pytest.fixture
    def adapter(self) -> BrowserToolAdapter:
        return BrowserToolAdapter(enabled=True)

    @pytest.mark.asyncio
    async def test_ssrf_private_url_blocked(self, adapter: BrowserToolAdapter) -> None:
        result = await adapter.execute(
            action="fetch",
            params={"url": "http://127.0.0.1/"},
        )
        assert result.success is False
        assert "security policy" in result.error or "rejected" in result.error

    @pytest.mark.asyncio
    async def test_unsafe_scheme_blocked(self, adapter: BrowserToolAdapter) -> None:
        result = await adapter.execute(
            action="fetch",
            params={"url": "file:///etc/passwd"},
        )
        assert result.success is False

    @pytest.mark.asyncio
    async def test_missing_url(self, adapter: BrowserToolAdapter) -> None:
        result = await adapter.execute(action="fetch", params={})
        assert result.success is False
        assert "url" in result.error

    @pytest.mark.asyncio
    async def test_disabled_adapter(self) -> None:
        disabled = BrowserToolAdapter(enabled=False)
        with pytest.raises(RuntimeError, match="is disabled"):
            await disabled.execute(
                action="fetch", params={"url": "https://example.com"}
            )


# ---------------------------------------------------------------------------
# Tool registry tests
# ---------------------------------------------------------------------------


class TestToolRegistry:
    """Tests for the tool registry."""

    def test_register_and_get_tool(self) -> None:
        adapter = MagicMock()
        register_tool("test-adapter", adapter)
        assert get_tool("test-adapter") is adapter

    def test_list_tools(self) -> None:
        tools = list_tools()
        assert "file" in tools
        assert "terminal" in tools
        assert "git" in tools
        assert "docker" in tools
        assert "mcp" in tools
        assert "browser" in tools

    def test_get_unknown_tool(self) -> None:
        assert get_tool("nonexistent") is None
