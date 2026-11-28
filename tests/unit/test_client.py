"""Unit tests for the Phase 10 JARVIS API client library."""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest

from jarvis.client import (
    JarvisAuthenticationError,
    JarvisClient,
    JarvisClientError,
)


def _transport(handler: Any) -> httpx.MockTransport:
    return httpx.MockTransport(handler)


def _json_response(payload: Any, status: int = 200) -> httpx.Response:
    return httpx.Response(status, json=payload)


def test_client_defaults_to_env_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("JARVIS_API_URL", "http://custom:9999")
    client = JarvisClient()
    assert client.base_url == "http://custom:9999"
    client.close()


def test_client_explicit_base_url() -> None:
    client = JarvisClient(base_url="http://127.0.0.1:8000")
    assert client.base_url == "http://127.0.0.1:8000"
    client.close()


def test_login_success_stores_token() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/v1/auth/login"
        body = json.loads(request.content)
        assert body["username"] == "alice"
        assert body["user_pwd"] == "secret"
        return _json_response(
            {
                "access_token": "tok-123",
                "refresh_token": "ref-456",
                "token_type": "bearer",
            }
        )

    client = JarvisClient(
        base_url="http://127.0.0.1:8000", transport=_transport(handler)
    )
    data = client.login(username="alice", password="secret")
    assert data["access_token"] == "tok-123"
    assert client.access_token == "tok-123"
    client.close()


def test_login_failure_raises_auth_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return _json_response({"detail": "Invalid username or password"}, status=401)

    client = JarvisClient(
        base_url="http://127.0.0.1:8000", transport=_transport(handler)
    )
    with pytest.raises(JarvisAuthenticationError):
        client.login(username="alice", password="wrong")
    client.close()


def test_login_server_error_raises_client_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return _json_response({"detail": "boom"}, status=500)

    client = JarvisClient(
        base_url="http://127.0.0.1:8000", transport=_transport(handler)
    )
    with pytest.raises(JarvisClientError):
        client.login(username="alice", password="secret")
    client.close()


def test_me_uses_bearer_token() -> None:
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["authorization"] = request.headers.get("authorization")
        return _json_response(
            {
                "id": "u-1",
                "username": "alice",
                "email": "alice@example.com",
                "is_active": True,
                "is_superuser": False,
            }
        )

    client = JarvisClient(
        base_url="http://127.0.0.1:8000",
        access_token="tok-abc",
        transport=_transport(handler),
    )
    profile = client.me()
    assert captured["authorization"] == "Bearer tok-abc"
    assert profile["username"] == "alice"
    assert profile["is_superuser"] is False
    client.close()


def test_me_without_token_raises_auth_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return _json_response({"detail": "Not authenticated"}, status=401)

    client = JarvisClient(
        base_url="http://127.0.0.1:8000", transport=_transport(handler)
    )
    with pytest.raises(JarvisAuthenticationError):
        client.me()
    client.close()


def test_health_and_ready() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/health":
            return _json_response({"status": "alive", "service": "jarvis"})
        return _json_response(
            {
                "status": "ready",
                "service": "jarvis",
                "checks": {"database": {"status": "up"}},
            }
        )

    client = JarvisClient(
        base_url="http://127.0.0.1:8000", transport=_transport(handler)
    )
    assert client.health()["status"] == "alive"
    assert client.ready()["status"] == "ready"
    client.close()


def test_speech_to_text_and_text_to_speech() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/v1/voice/speech-to-text":
            return _json_response(
                {"text": "hello", "confidence": 0.95, "provider": "local"}
            )
        return _json_response(
            {"audio_bytes": "", "content_type": "audio/wav", "provider": "local"}
        )

    client = JarvisClient(
        base_url="http://127.0.0.1:8000", transport=_transport(handler)
    )
    stt = client.speech_to_text(audio_b64="base64audio", language="en-US")
    assert stt["text"] == "hello"
    assert stt["confidence"] == 0.95
    tts = client.text_to_speech(text="hello", voice="alloy", language="en")
    assert tts["content_type"] == "audio/wav"
    client.close()


def test_describe_and_analyze_image() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/v1/vision/describe":
            return _json_response(
                {"description": "a cat", "confidence": 0.9, "provider": "local"}
            )
        body = json.loads(request.content)
        assert body["questions"] == ["What color?", "What shape?"]
        return _json_response(
            {
                "answers": {"What color?": "orange", "What shape?": "round"},
                "provider": "local",
            }
        )

    client = JarvisClient(
        base_url="http://127.0.0.1:8000", transport=_transport(handler)
    )
    desc = client.describe_image(image_b64="base64img", prompt="What is this?")
    assert desc["description"] == "a cat"
    ans = client.analyze_image(
        image_b64="base64img", questions=["What color?", "What shape?"]
    )
    assert ans["answers"]["What color?"] == "orange"
    client.close()


def test_smart_environment_crud() -> None:
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path)
        if request.url.path == "/api/v1/smart-environment/devices":
            return _json_response({"devices": [{"id": "d1", "name": "Light"}]})
        if request.url.path == "/api/v1/smart-environment/devices/d1/state":
            if request.method == "GET":
                return _json_response({"device_id": "d1", "state": {"on": True}})
            body = json.loads(request.content)
            assert body["state"] == {"on": "true"}
            return _json_response({"device_id": "d1", "state": {"on": True}})
        return _json_response({}, status=404)

    client = JarvisClient(
        base_url="http://127.0.0.1:8000", transport=_transport(handler)
    )
    devs = client.list_devices()
    assert devs["devices"][0]["name"] == "Light"
    state = client.get_device_state("d1")
    assert state["state"] == {"on": True}
    updated = client.set_device_state("d1", {"on": "true"})
    assert updated["state"] == {"on": True}
    assert "/api/v1/smart-environment/devices/d1/state" in calls
    client.close()


def test_context_manager_closes() -> None:
    client = JarvisClient(base_url="http://127.0.0.1:8000")
    with client:
        assert client._client.is_closed is False
    assert client._client.is_closed is True
