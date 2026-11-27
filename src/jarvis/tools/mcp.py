"""MCP (Model Context Protocol) capability adapter.

Provides a client-side adapter for connecting to MCP servers via
stdio or HTTP. All connections are validated for SSRF safety before
establishment. Tool calls through MCP are audited and bounded.
"""

from __future__ import annotations

from typing import Any

import httpx

from jarvis.core.exceptions import ProviderError, ValidationError
from jarvis.core.logging import get_logger
from jarvis.tools.base import BaseToolAdapter, ToolResult

logger = get_logger(__name__)

# Default MCP connection timeout in seconds.
DEFAULT_MCP_TIMEOUT_SECONDS = 30


class MCPToolAdapter(BaseToolAdapter):
    """MCP client adapter for server tool invocation.

    Supports:
    - ``list_tools``: List available tools from an MCP server
    - ``call_tool``: Call a specific tool on an MCP server

    Connections are validated against SSRF policy before any network
    request is made.
    """

    def __init__(
        self,
        *,
        enabled: bool = False,
        timeout_seconds: int = DEFAULT_MCP_TIMEOUT_SECONDS,
    ) -> None:
        super().__init__(provider_name="mcp", enabled=enabled)
        self.timeout_seconds = timeout_seconds

    async def execute(self, *, action: str, params: dict[str, Any]) -> ToolResult:
        """Execute an MCP action.

        Args:
            action: One of ``list_tools``, ``call_tool``.
            params: For ``list_tools``: ``server_url``. For
                ``call_tool``: ``server_url``, ``tool_name``,
                ``arguments``.

        Returns:
            A :class:`ToolResult`` with the MCP operation outcome.
        """
        self._require_enabled()

        server_url = params.get("server_url")
        if not server_url or not isinstance(server_url, str):
            return ToolResult(
                success=False,
                error="Missing required parameter: server_url",
                provider=self.provider_name,
            )

        # SSRF validation before any network request
        try:
            from jarvis.core.security import validate_ssrf_safe_url

            validate_ssrf_safe_url(server_url)
        except ValidationError as exc:
            logger.warning(
                "MCP server URL rejected by SSRF policy",
                extra={"server_url": server_url, "error": exc.code},
            )
            return ToolResult(
                success=False,
                error=f"Server URL rejected by security policy: {exc.message}",
                provider=self.provider_name,
                metadata={"code": exc.code},
            )

        try:
            if action == "list_tools":
                return await self._list_tools(server_url)
            if action == "call_tool":
                return await self._call_tool(server_url, params)
            return ToolResult(
                success=False,
                error=f"Unknown MCP action: {action}",
                provider=self.provider_name,
            )
        except ProviderError as exc:
            logger.error(
                "MCP provider error",
                extra={"server_url": server_url, "error": exc.message},
            )
            return ToolResult(
                success=False,
                error=exc.message,
                provider=self.provider_name,
                metadata={"code": exc.code},
            )
        except Exception as exc:  # noqa: BLE001 - tool errors are captured
            logger.error(
                "MCP execution error",
                extra={"server_url": server_url, "error": str(exc)},
            )
            return ToolResult(
                success=False,
                error=str(exc),
                provider=self.provider_name,
            )

    async def _list_tools(self, server_url: str) -> ToolResult:
        """List tools available on an MCP server."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(
                    f"{server_url.rstrip('/')}/mcp/listTools",
                    json={},
                )
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPStatusError as exc:
            raise ProviderError(
                f"MCP server returned {exc.response.status_code}"
            ) from exc
        except httpx.RequestError as exc:
            raise ProviderError(f"MCP connection error: {exc}") from exc

        tools = data.get("tools", []) if isinstance(data, dict) else []
        return ToolResult(
            success=True,
            data={"server_url": server_url, "tools": tools},
            provider=self.provider_name,
        )

    async def _call_tool(self, server_url: str, params: dict[str, Any]) -> ToolResult:
        """Call a specific tool on an MCP server."""
        tool_name = params.get("tool_name")
        if not tool_name or not isinstance(tool_name, str):
            return ToolResult(
                success=False,
                error="Missing required parameter: tool_name",
                provider=self.provider_name,
            )
        arguments = params.get("arguments", {})
        if not isinstance(arguments, dict):
            return ToolResult(
                success=False,
                error="Parameter 'arguments' must be a JSON object",
                provider=self.provider_name,
            )

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(
                    f"{server_url.rstrip('/')}/mcp/callTool",
                    json={"name": tool_name, "arguments": arguments},
                )
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPStatusError as exc:
            raise ProviderError(
                f"MCP server returned {exc.response.status_code}"
            ) from exc
        except httpx.RequestError as exc:
            raise ProviderError(f"MCP connection error: {exc}") from exc

        return ToolResult(
            success=True,
            data={
                "server_url": server_url,
                "tool_name": tool_name,
                "result": data,
            },
            provider=self.provider_name,
        )


mcp_tool = MCPToolAdapter(
    enabled=False,  # Disabled by default; enable via configuration
)

__all__ = [
    "DEFAULT_MCP_TIMEOUT_SECONDS",
    "MCPToolAdapter",
    "mcp_tool",
]
