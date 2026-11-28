"""Unit tests for the JARVIS operator CLI (Phase 10)."""

from __future__ import annotations

import argparse
import json
from typing import Any

import httpx
import pytest

from jarvis.client.api import JarvisClient
from jarvis.client.cli import (
    build_parser,
    cmd_agents_create,
    cmd_agents_list,
    cmd_approvals_request,
    cmd_conversations_send,
    cmd_health,
    cmd_login,
    cmd_me,
    cmd_memory_ingest,
    cmd_memory_search,
    cmd_tasks_create,
    cmd_tasks_get,
    cmd_tasks_list,
    main,
)


def _transport(handler: Any) -> httpx.MockTransport:
    def mock_handler(request: httpx.Request) -> httpx.Response:
        return handler(request)

    return httpx.MockTransport(mock_handler)


def _client(handler: Any, token: str | None = "test-token") -> JarvisClient:
    return JarvisClient(
        base_url="http://127.0.0.1:8000",
        access_token=token,
        transport=_transport(handler),
    )


def _args(**kwargs: Any) -> argparse.Namespace:
    ns = argparse.Namespace(
        url="http://127.0.0.1:8000",
        token="test-token",
        command=None,
        subcommand=None,
        state=None,
        agent_id=None,
        limit=100,
        is_active=False,
        no_is_active=False,
        task_type=None,
        risk_classification="low",
        idempotency_key=None,
        task_id=None,
        name=None,
        version=None,
        description=None,
        max_runtime_seconds=300,
        max_tool_calls=50,
        title=None,
        conversation_id=None,
        content=None,
        memory_type=None,
        source=None,
        source_type=None,
        source_id=None,
        confidence=None,
        chunk_size=1000,
        overlap=200,
        query=None,
        threshold=0.0,
        expires_in_minutes=60,
        approval_id=None,
        username=None,
        password=None,
    )
    for key, value in kwargs.items():
        setattr(ns, key, value)
    return ns


class TestParser:
    """Tests for the argument parser structure."""

    def test_build_parser_has_expected_commands(self) -> None:
        parser = build_parser()
        expected = {
            "login",
            "me",
            "health",
            "ready",
            "metrics",
            "tasks",
            "agents",
            "conversations",
            "memory",
            "approvals",
        }
        sub = next(a for a in parser._actions if a.dest == "command")
        assert set(sub.choices) == expected

    def test_login_requires_username_password(self) -> None:
        parser = build_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["login"])

    def test_tasks_create_requires_task_type(self) -> None:
        parser = build_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["tasks", "create"])


class TestHandlers:
    """Tests for CLI command handlers with mocked HTTP transport."""

    def test_login(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            assert request.url.path == "/api/v1/auth/login"
            return httpx.Response(200, json={"access_token": "tok-123"})

        client = _client(handler)
        ns = _args(command="login", username="alice", password="secret")
        assert cmd_login(ns, client) == 0

    def test_me(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            assert request.headers["authorization"] == "Bearer test-token"
            return httpx.Response(200, json={"username": "alice"})

        client = _client(handler)
        ns = _args(command="me")
        assert cmd_me(ns, client) == 0

    def test_health(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"status": "ok"})

        client = _client(handler)
        ns = _args(command="health")
        assert cmd_health(ns, client) == 0

    def test_tasks_list(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=[{"id": "t1", "task_type": "ops"}])

        client = _client(handler)
        ns = _args(command="tasks", subcommand="list", state="queued", limit=10)
        assert cmd_tasks_list(ns, client) == 0

    def test_tasks_create(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            body = json.loads(request.content)
            assert body["task_type"] == "backup"
            return httpx.Response(201, json={"id": "t2"})

        client = _client(handler)
        ns = _args(
            command="tasks",
            subcommand="create",
            task_type="backup",
            risk_classification="medium",
            agent_id="a1",
            idempotency_key="k1",
        )
        assert cmd_tasks_create(ns, client) == 0

    def test_tasks_get(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            assert request.url.path == "/api/v1/tasks/t1"
            return httpx.Response(200, json={"id": "t1"})

        client = _client(handler)
        ns = _args(command="tasks", subcommand="get", task_id="t1")
        assert cmd_tasks_get(ns, client) == 0

    def test_agents_list(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=[{"id": "a1", "name": "reviewer"}])

        client = _client(handler)
        ns = _args(command="agents", subcommand="list", limit=50)
        assert cmd_agents_list(ns, client) == 0

    def test_agents_create(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(201, json={"id": "a2"})

        client = _client(handler)
        ns = _args(
            command="agents",
            subcommand="create",
            name="coder",
            version="2.0.0",
            description="desc",
            max_runtime_seconds=600,
            max_tool_calls=100,
        )
        assert cmd_agents_create(ns, client) == 0

    def test_conversations_send(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            assert request.url.path == "/api/v1/conversations/c1/messages"
            return httpx.Response(200, json={"id": "m1"})

        client = _client(handler)
        ns = _args(
            command="conversations",
            subcommand="send",
            conversation_id="c1",
            content="hello",
        )
        assert cmd_conversations_send(ns, client) == 0

    def test_memory_ingest(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            assert request.url.path == "/api/v1/memory/ingest"
            return httpx.Response(201, json={"ingested": 2})

        client = _client(handler)
        ns = _args(
            command="memory",
            subcommand="ingest",
            content="doc text",
            source="notes.txt",
            source_type="document",
            source_id="s1",
            memory_type="semantic",
            confidence=90,
            chunk_size=500,
            overlap=50,
        )
        assert cmd_memory_ingest(ns, client) == 0

    def test_memory_search(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            assert request.url.path == "/api/v1/memory/search"
            return httpx.Response(200, json=[])

        client = _client(handler)
        ns = _args(
            command="memory",
            subcommand="search",
            query="foo",
            memory_type="semantic",
            limit=5,
            threshold=0.3,
        )
        assert cmd_memory_search(ns, client) == 0

    def test_approvals_request(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            assert request.url.path == "/api/v1/approvals"
            return httpx.Response(200, json={"id": "ap1"})

        client = _client(handler)
        ns = _args(
            command="approvals",
            subcommand="request",
            task_id="t1",
            expires_in_minutes=30,
        )
        assert cmd_approvals_request(ns, client) == 0

    def test_authentication_error(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(401, json={"detail": "invalid"})

        client = _client(handler)
        ns = _args(command="me")
        assert cmd_me(ns, client) == 1


class TestMain:
    """Tests for the main entry point."""

    def test_main_no_command(self) -> None:
        # Required subparsers: argparse exits 2 when no command is given.
        assert main([]) == 2

    def test_main_help(self) -> None:
        assert main(["--help"]) == 0
