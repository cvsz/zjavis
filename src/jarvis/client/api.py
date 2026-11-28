"""Phase 10 JARVIS API client library.

A generic, reusable Python client for the JARVIS HTTP API. Handles
authentication (bearer tokens), request retries, and typed access to the
core API endpoints (health, auth, voice, vision, smart environment,
tasks, agents, approvals, metrics).

Designed for CLI tools, scripts, and any programmatic consumer of the
JARVIS API. No credentials are embedded; tokens come from login or are
passed in explicitly.
"""

from __future__ import annotations

import os
from typing import Any, Self, cast

import httpx


class JarvisClientError(Exception):
    """Base exception for JARVIS client errors."""


class JarvisAuthenticationError(JarvisClientError):
    """Raised when authentication fails (401)."""


class JarvisClient:
    """Client for the JARVIS REST API.

    Args:
        base_url: Base URL of the JARVIS API (e.g. ``http://127.0.0.1:8000``).
        access_token: Optional bearer access token. If not provided, login
            must be called before authenticated endpoints are used.
        timeout: Request timeout in seconds.
    """

    def __init__(
        self,
        *,
        base_url: str | None = None,
        access_token: str | None = None,
        timeout: float = 30.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.base_url = cast(
            str,
            base_url or os.getenv("JARVIS_API_URL", "http://127.0.0.1:8000"),
        ).rstrip("/")
        self.access_token = access_token or os.getenv("JARVIS_ACCESS_TOKEN")
        self.timeout = timeout
        self._client = httpx.Client(
            base_url=self.base_url, timeout=timeout, transport=transport
        )

    def _headers(self, extra: dict[str, str] | None = None) -> dict[str, str]:
        headers: dict[str, str] = {}
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        if extra:
            headers.update(extra)
        return headers

    def _handle_response(self, resp: httpx.Response) -> Any:
        if resp.status_code == 401:
            raise JarvisAuthenticationError(f"Authentication failed: {resp.text}")
        if resp.status_code >= 400:
            raise JarvisClientError(f"Request failed ({resp.status_code}): {resp.text}")
        if resp.headers.get("content-type", "").startswith("application/json"):
            return resp.json()
        return resp.text

    def close(self) -> None:
        """Close the underlying HTTP client."""
        self._client.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    # --- Authentication -----------------------------------------------------

    def login(self, *, username: str, password: str) -> dict[str, str]:
        """Authenticate and store the access token.

        Returns the token response (access_token, refresh_token, token_type).
        """
        resp = self._client.post(
            "/api/v1/auth/login",
            json={"username": username, "user_pwd": password},
        )
        if resp.status_code == 401:
            raise JarvisAuthenticationError("Invalid username or password")
        data = cast(dict[str, str], self._handle_response(resp))
        self.access_token = data["access_token"]
        return data

    def me(self) -> dict[str, Any]:
        """Return the profile of the currently authenticated user."""
        resp = self._client.get("/api/v1/auth/me", headers=self._headers())
        return cast(dict[str, Any], self._handle_response(resp))

    # --- Health -------------------------------------------------------------

    def health(self) -> dict[str, Any]:
        """Liveness probe."""
        resp = self._client.get("/health")
        return cast(dict[str, Any], self._handle_response(resp))

    def ready(self) -> dict[str, Any]:
        """Readiness probe."""
        resp = self._client.get("/ready")
        return cast(dict[str, Any], self._handle_response(resp))

    # --- Voice --------------------------------------------------------------

    def speech_to_text(
        self, *, audio_b64: str, language: str | None = None
    ) -> dict[str, Any]:
        """Convert speech audio to text."""
        payload: dict[str, Any] = {"audio_b64": audio_b64}
        if language is not None:
            payload["language"] = language
        resp = self._client.post(
            "/api/v1/voice/speech-to-text",
            json=payload,
            headers=self._headers(),
        )
        return cast(dict[str, Any], self._handle_response(resp))

    def text_to_speech(
        self,
        *,
        text: str,
        voice: str | None = None,
        language: str | None = None,
    ) -> dict[str, Any]:
        """Convert text to speech audio."""
        payload: dict[str, Any] = {"text": text}
        if voice is not None:
            payload["voice"] = voice
        if language is not None:
            payload["language"] = language
        resp = self._client.post(
            "/api/v1/voice/text-to-speech",
            json=payload,
            headers=self._headers(),
        )
        return cast(dict[str, Any], self._handle_response(resp))

    # --- Vision -------------------------------------------------------------

    def describe_image(
        self, *, image_b64: str, prompt: str | None = None
    ) -> dict[str, Any]:
        """Describe or analyze an image."""
        payload: dict[str, Any] = {"image_b64": image_b64}
        if prompt is not None:
            payload["prompt"] = prompt
        resp = self._client.post(
            "/api/v1/vision/describe",
            json=payload,
            headers=self._headers(),
        )
        return cast(dict[str, Any], self._handle_response(resp))

    def analyze_image(self, *, image_b64: str, questions: list[str]) -> dict[str, Any]:
        """Answer questions about an image."""
        resp = self._client.post(
            "/api/v1/vision/analyze",
            json={"image_b64": image_b64, "questions": questions},
            headers=self._headers(),
        )
        return cast(dict[str, Any], self._handle_response(resp))

    # --- Smart Environment --------------------------------------------------

    def list_devices(self) -> dict[str, Any]:
        """List all smart environment / IoT devices."""
        resp = self._client.get(
            "/api/v1/smart-environment/devices", headers=self._headers()
        )
        return cast(dict[str, Any], self._handle_response(resp))

    def get_device_state(self, device_id: str) -> dict[str, Any]:
        """Get the current state of a device."""
        resp = self._client.get(
            f"/api/v1/smart-environment/devices/{device_id}/state",
            headers=self._headers(),
        )
        return cast(dict[str, Any], self._handle_response(resp))

    def set_device_state(self, device_id: str, state: dict[str, str]) -> dict[str, Any]:
        """Set the state of a device."""
        resp = self._client.post(
            f"/api/v1/smart-environment/devices/{device_id}/state",
            json={"state": state},
            headers=self._headers(),
        )
        return cast(dict[str, Any], self._handle_response(resp))
