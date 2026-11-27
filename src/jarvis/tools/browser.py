"""Browser capability adapter.

Provides authorized, read-only web browsing with SSRF prevention.
Navigation is restricted to public HTTPS URLs only; private/reserved
addresses and non-HTTP(S) schemes are rejected. Page content is fetched
and returned without executing JavaScript or retaining session state.
"""

from __future__ import annotations

from typing import Any

import httpx

from jarvis.core.exceptions import ProviderError, ValidationError
from jarvis.core.logging import get_logger
from jarvis.core.security import validate_ssrf_safe_url
from jarvis.tools.base import BaseToolAdapter, ToolResult

logger = get_logger(__name__)

# Default browser fetch timeout in seconds.
DEFAULT_BROWSER_TIMEOUT_SECONDS = 30

# Maximum page content size in bytes to prevent resource exhaustion.
MAX_PAGE_BYTES = 5_000_000  # 5 MB

# Allowed content types for browsing.
ALLOWED_CONTENT_TYPES: frozenset[str] = frozenset(
    {
        "text/html",
        "text/plain",
        "text/markdown",
        "application/json",
        "application/xhtml+xml",
    }
)


class BrowserToolAdapter(BaseToolAdapter):
    """Read-only browser adapter with SSRF prevention.

    Supports:
    - ``fetch``: Fetch a URL and return its text content.

    Security controls:
    - Only http/https schemes permitted
    - Private/reserved IPv4 addresses rejected (SSRF)
    - Response size bounded
    - No JavaScript execution
    - No cookie/session persistence
    """

    def __init__(
        self,
        *,
        enabled: bool = False,
        timeout_seconds: int = DEFAULT_BROWSER_TIMEOUT_SECONDS,
    ) -> None:
        super().__init__(provider_name="browser", enabled=enabled)
        self.timeout_seconds = timeout_seconds

    async def execute(self, *, action: str, params: dict[str, Any]) -> ToolResult:
        """Execute a browser action.

        Args:
            action: One of ``fetch``.
            params: Must include ``url`` (http/https URL).

        Returns:
            A :class:`ToolResult`` with the page content.
        """
        self._require_enabled()

        url = params.get("url")
        if not url or not isinstance(url, str):
            return ToolResult(
                success=False,
                error="Missing required parameter: url",
                provider=self.provider_name,
            )

        # SSRF validation before any network request
        try:
            validate_ssrf_safe_url(url)
        except ValidationError as exc:
            logger.warning(
                "Browser URL rejected by SSRF policy",
                extra={"url": url, "error": exc.code},
            )
            return ToolResult(
                success=False,
                error=f"URL rejected by security policy: {exc.message}",
                provider=self.provider_name,
                metadata={"code": exc.code},
            )

        try:
            return await self._fetch(url)
        except ProviderError as exc:
            logger.error(
                "Browser fetch error",
                extra={"url": url, "error": exc.message},
            )
            return ToolResult(
                success=False,
                error=exc.message,
                provider=self.provider_name,
                metadata={"code": exc.code},
            )
        except Exception as exc:  # noqa: BLE001 - tool errors are captured
            logger.error(
                "Browser execution error",
                extra={"url": url, "error": str(exc)},
            )
            return ToolResult(
                success=False,
                error=str(exc),
                provider=self.provider_name,
            )

    async def _fetch(self, url: str) -> ToolResult:
        """Fetch a URL and return its text content."""
        headers = {
            "User-Agent": "JARVIS-Browser/1.0 (compatible; read-only; no JS)",
            "Accept": "text/html, text/plain, application/json",
        }

        try:
            async with httpx.AsyncClient(
                timeout=self.timeout_seconds, follow_redirects=True
            ) as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise ProviderError(f"Server returned {exc.response.status_code}") from exc
        except httpx.RequestError as exc:
            raise ProviderError(f"Connection error: {exc}") from exc

        content_type = response.headers.get("content-type", "").split(";")[0].strip()
        if content_type and content_type not in ALLOWED_CONTENT_TYPES:
            return ToolResult(
                success=False,
                error=f"Content type not permitted: {content_type}",
                provider=self.provider_name,
            )

        content = response.text[:MAX_PAGE_BYTES]

        return ToolResult(
            success=True,
            data={
                "url": str(response.url),
                "status_code": response.status_code,
                "content_type": content_type,
                "content": content,
                "content_length": len(content),
            },
            provider=self.provider_name,
        )


browser_tool = BrowserToolAdapter(
    enabled=False,  # Disabled by default; enable via configuration
)

__all__ = [
    "DEFAULT_BROWSER_TIMEOUT_SECONDS",
    "MAX_PAGE_BYTES",
    "BrowserToolAdapter",
    "browser_tool",
]
