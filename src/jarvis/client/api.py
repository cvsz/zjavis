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

    # --- Tasks --------------------------------------------------------------

    def list_tasks(
        self,
        *,
        state: str | None = None,
        agent_id: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """List tasks for the authenticated user's tenant."""
        params: dict[str, Any] = {"limit": limit}
        if state is not None:
            params["state"] = state
        if agent_id is not None:
            params["agent_id"] = agent_id
        resp = self._client.get("/api/v1/tasks", params=params, headers=self._headers())
        return cast(list[dict[str, Any]], self._handle_response(resp))

    def create_task(
        self,
        *,
        task_type: str,
        risk_classification: str = "low",
        agent_id: str | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        """Create a new task."""
        payload: dict[str, Any] = {"task_type": task_type}
        if risk_classification is not None:
            payload["risk_classification"] = risk_classification
        if agent_id is not None:
            payload["agent_id"] = agent_id
        if idempotency_key is not None:
            payload["idempotency_key"] = idempotency_key
        resp = self._client.post("/api/v1/tasks", json=payload, headers=self._headers())
        return cast(dict[str, Any], self._handle_response(resp))

    def get_task(self, task_id: str) -> dict[str, Any]:
        """Get a single task by ID."""
        resp = self._client.get(f"/api/v1/tasks/{task_id}", headers=self._headers())
        return cast(dict[str, Any], self._handle_response(resp))

    def update_task(
        self,
        *,
        task_id: str,
        task_type: str | None = None,
        risk_classification: str | None = None,
        agent_id: str | None = None,
    ) -> dict[str, Any]:
        """Update an existing task."""
        payload: dict[str, Any] = {}
        if task_type is not None:
            payload["task_type"] = task_type
        if risk_classification is not None:
            payload["risk_classification"] = risk_classification
        if agent_id is not None:
            payload["agent_id"] = agent_id
        resp = self._client.patch(
            f"/api/v1/tasks/{task_id}", json=payload, headers=self._headers()
        )
        return cast(dict[str, Any], self._handle_response(resp))

    def delete_task(self, task_id: str) -> dict[str, Any]:
        """Delete a task by ID."""
        resp = self._client.delete(f"/api/v1/tasks/{task_id}", headers=self._headers())
        return cast(dict[str, Any], self._handle_response(resp))

    # --- Agents -------------------------------------------------------------

    def list_agents(
        self,
        *,
        is_active: bool | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """List agents for the authenticated user's tenant."""
        params: dict[str, Any] = {"limit": limit}
        if is_active is not None:
            params["is_active"] = str(is_active).lower()
        resp = self._client.get(
            "/api/v1/agents", params=params, headers=self._headers()
        )
        return cast(list[dict[str, Any]], self._handle_response(resp))

    def create_agent(
        self,
        *,
        name: str,
        version: str = "1.0.0",
        description: str | None = None,
        max_runtime_seconds: int = 300,
        max_tool_calls: int = 50,
    ) -> dict[str, Any]:
        """Create a new agent definition."""
        payload: dict[str, Any] = {
            "name": name,
            "version": version,
            "max_runtime_seconds": max_runtime_seconds,
            "max_tool_calls": max_tool_calls,
        }
        if description is not None:
            payload["description"] = description
        resp = self._client.post(
            "/api/v1/agents", json=payload, headers=self._headers()
        )
        return cast(dict[str, Any], self._handle_response(resp))

    def get_agent(self, agent_id: str) -> dict[str, Any]:
        """Get a single agent by ID."""
        resp = self._client.get(f"/api/v1/agents/{agent_id}", headers=self._headers())
        return cast(dict[str, Any], self._handle_response(resp))

    def update_agent(
        self,
        *,
        agent_id: str,
        name: str | None = None,
        version: str | None = None,
        description: str | None = None,
        is_active: bool | None = None,
    ) -> dict[str, Any]:
        """Update an existing agent."""
        payload: dict[str, Any] = {}
        if name is not None:
            payload["name"] = name
        if version is not None:
            payload["version"] = version
        if description is not None:
            payload["description"] = description
        if is_active is not None:
            payload["is_active"] = is_active
        resp = self._client.patch(
            f"/api/v1/agents/{agent_id}", json=payload, headers=self._headers()
        )
        return cast(dict[str, Any], self._handle_response(resp))

    def delete_agent(self, agent_id: str) -> dict[str, Any]:
        """Delete an agent by ID."""
        resp = self._client.delete(
            f"/api/v1/agents/{agent_id}", headers=self._headers()
        )
        return cast(dict[str, Any], self._handle_response(resp))

    # --- Approvals ----------------------------------------------------------

    def request_approval(
        self,
        *,
        task_id: str,
        expires_in_minutes: int = 60,
    ) -> dict[str, Any]:
        """Request approval for a consequential action."""
        payload: dict[str, Any] = {
            "task_id": task_id,
            "expires_in_minutes": expires_in_minutes,
        }
        resp = self._client.post(
            "/api/v1/approvals", json=payload, headers=self._headers()
        )
        return cast(dict[str, Any], self._handle_response(resp))

    def list_approvals(
        self,
        *,
        state: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """List approval requests for the authenticated user's tenant."""
        params: dict[str, Any] = {"limit": limit}
        if state is not None:
            params["state"] = state
        resp = self._client.get(
            "/api/v1/approvals", params=params, headers=self._headers()
        )
        return cast(list[dict[str, Any]], self._handle_response(resp))

    def approve_approval(self, *, approval_id: str) -> dict[str, Any]:
        """Approve a pending approval request."""
        resp = self._client.post(
            f"/api/v1/approvals/{approval_id}/approve", headers=self._headers()
        )
        return cast(dict[str, Any], self._handle_response(resp))

    def deny_approval(self, *, approval_id: str) -> dict[str, Any]:
        """Deny a pending approval request."""
        resp = self._client.post(
            f"/api/v1/approvals/{approval_id}/deny", headers=self._headers()
        )
        return cast(dict[str, Any], self._handle_response(resp))

    # --- Metrics ------------------------------------------------------------

    def metrics(self) -> str:
        """Return Prometheus metrics text."""
        resp = self._client.get("/metrics", headers=self._headers())
        return cast(str, self._handle_response(resp))

    # --- Conversations ------------------------------------------------------

    def list_conversations(
        self,
        *,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """List conversations for the authenticated user's tenant."""
        params: dict[str, Any] = {"limit": limit}
        resp = self._client.get(
            "/api/v1/conversations", params=params, headers=self._headers()
        )
        return cast(list[dict[str, Any]], self._handle_response(resp))

    def create_conversation(
        self,
        *,
        title: str | None = None,
    ) -> dict[str, Any]:
        """Create a new conversation."""
        payload: dict[str, Any] = {}
        if title is not None:
            payload["title"] = title
        resp = self._client.post(
            "/api/v1/conversations", json=payload, headers=self._headers()
        )
        return cast(dict[str, Any], self._handle_response(resp))

    def get_conversation(self, conversation_id: str) -> dict[str, Any]:
        """Get a single conversation by ID."""
        resp = self._client.get(
            f"/api/v1/conversations/{conversation_id}", headers=self._headers()
        )
        return cast(dict[str, Any], self._handle_response(resp))

    def send_message(
        self,
        *,
        conversation_id: str,
        content: str,
    ) -> dict[str, Any]:
        """Send a message in a conversation."""
        payload: dict[str, Any] = {"content": content}
        resp = self._client.post(
            f"/api/v1/conversations/{conversation_id}/messages",
            json=payload,
            headers=self._headers(),
        )
        return cast(dict[str, Any], self._handle_response(resp))

    # --- Memory -------------------------------------------------------------

    def list_memory(
        self,
        *,
        memory_type: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """List memory items for the authenticated user's tenant."""
        params: dict[str, Any] = {"limit": limit}
        if memory_type is not None:
            params["memory_type"] = memory_type
        resp = self._client.get(
            "/api/v1/memory", params=params, headers=self._headers()
        )
        return cast(list[dict[str, Any]], self._handle_response(resp))

    def create_memory(
        self,
        *,
        content: str,
        memory_type: str = "conversation",
        source: str | None = None,
        source_type: str | None = None,
        source_id: str | None = None,
        confidence: int | None = None,
    ) -> dict[str, Any]:
        """Create a new memory item."""
        payload: dict[str, Any] = {
            "content": content,
            "memory_type": memory_type,
        }
        if source is not None:
            payload["source"] = source
        if source_type is not None:
            payload["source_type"] = source_type
        if source_id is not None:
            payload["source_id"] = source_id
        if confidence is not None:
            payload["confidence"] = confidence
        resp = self._client.post(
            "/api/v1/memory", json=payload, headers=self._headers()
        )
        return cast(dict[str, Any], self._handle_response(resp))

    def search_memory(
        self,
        *,
        query: str,
        memory_type: str | None = None,
        limit: int = 10,
        threshold: float = 0.0,
    ) -> list[dict[str, Any]]:
        """Semantic (vector-similarity) search across tenant memories."""
        payload: dict[str, Any] = {
            "query": query,
            "limit": limit,
            "threshold": threshold,
        }
        if memory_type is not None:
            payload["memory_type"] = memory_type
        resp = self._client.post(
            "/api/v1/memory/search", json=payload, headers=self._headers()
        )
        return cast(list[dict[str, Any]], self._handle_response(resp))

    def ingest_document(
        self,
        *,
        content: str,
        source: str,
        source_type: str = "document",
        source_id: str | None = None,
        memory_type: str = "semantic",
        confidence: int | None = 80,
        chunk_size: int = 1000,
        overlap: int = 200,
    ) -> dict[str, Any]:
        """Ingest a document into memory: chunk, embed, and store each chunk."""
        payload: dict[str, Any] = {
            "content": content,
            "source": source,
            "source_type": source_type,
            "memory_type": memory_type,
            "confidence": confidence,
            "chunk_size": chunk_size,
            "overlap": overlap,
        }
        if source_id is not None:
            payload["source_id"] = source_id
        resp = self._client.post(
            "/api/v1/memory/ingest", json=payload, headers=self._headers()
        )
        return cast(dict[str, Any], self._handle_response(resp))

    # --- Audit --------------------------------------------------------------

    def list_audit_events(
        self,
        *,
        event_type: str | None = None,
        event_category: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """List audit events for the authenticated user's tenant."""
        params: dict[str, Any] = {"limit": limit}
        if event_type is not None:
            params["event_type"] = event_type
        if event_category is not None:
            params["event_category"] = event_category
        resp = self._client.get(
            "/api/v1/audit/events", params=params, headers=self._headers()
        )
        return cast(list[dict[str, Any]], self._handle_response(resp))
