"""Phase 10 JARVIS operator command-line interface.

A thin argparse-based CLI around :class:`jarvis.client.api.JarvisClient`,
giving operators a terminal surface for the JARVIS HTTP API:

    jarvis-cli login --username alice --password secret
    jarvis-cli --token <token> health
    jarvis-cli --token <token> tasks list
    jarvis-cli --token <token> memory ingest --source notes.txt --content "..."

No credentials are embedded; tokens come from ``--token``, the
``JARVIS_ACCESS_TOKEN`` environment variable, or ``login`` output.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Callable
from typing import Any, cast

from jarvis.client.api import (
    JarvisAuthenticationError,
    JarvisClient,
    JarvisClientError,
)

DEFAULT_URL = os.getenv("JARVIS_API_URL", "http://127.0.0.1:8000")


def _client(url: str | None, token: str | None) -> JarvisClient:
    return JarvisClient(
        base_url=url or DEFAULT_URL,
        access_token=token or os.getenv("JARVIS_ACCESS_TOKEN"),
    )


def _print(data: Any) -> None:
    """Print data as JSON when structured, otherwise as-is."""
    if isinstance(data, (dict, list)):
        print(json.dumps(data, indent=2, default=str))
    else:
        print(data)


def _error(message: str) -> int:
    print(f"error: {message}", file=sys.stderr)
    return 1


# --- command handlers -------------------------------------------------------


def cmd_login(args: argparse.Namespace, client: JarvisClient) -> int:
    try:
        data = client.login(username=args.username, password=args.password)
    except JarvisAuthenticationError as exc:
        return _error(str(exc))
    print(data.get("access_token", ""))
    return 0


def cmd_me(args: argparse.Namespace, client: JarvisClient) -> int:
    try:
        _print(client.me())
    except JarvisClientError as exc:
        return _error(str(exc))
    return 0


def cmd_health(args: argparse.Namespace, client: JarvisClient) -> int:
    try:
        _print(client.health())
    except JarvisClientError as exc:
        return _error(str(exc))
    return 0


def cmd_ready(args: argparse.Namespace, client: JarvisClient) -> int:
    try:
        _print(client.ready())
    except JarvisClientError as exc:
        return _error(str(exc))
    return 0


def cmd_metrics(args: argparse.Namespace, client: JarvisClient) -> int:
    try:
        print(client.metrics())
    except JarvisClientError as exc:
        return _error(str(exc))
    return 0


def cmd_tasks_list(args: argparse.Namespace, client: JarvisClient) -> int:
    try:
        _print(
            client.list_tasks(
                state=args.state, agent_id=args.agent_id, limit=args.limit
            )
        )
    except JarvisClientError as exc:
        return _error(str(exc))
    return 0


def cmd_tasks_create(args: argparse.Namespace, client: JarvisClient) -> int:
    try:
        _print(
            client.create_task(
                task_type=args.task_type,
                risk_classification=args.risk_classification,
                agent_id=args.agent_id,
                idempotency_key=args.idempotency_key,
            )
        )
    except JarvisClientError as exc:
        return _error(str(exc))
    return 0


def cmd_tasks_get(args: argparse.Namespace, client: JarvisClient) -> int:
    try:
        _print(client.get_task(args.task_id))
    except JarvisClientError as exc:
        return _error(str(exc))
    return 0


def cmd_agents_list(args: argparse.Namespace, client: JarvisClient) -> int:
    try:
        _print(client.list_agents(is_active=args.is_active, limit=args.limit))
    except JarvisClientError as exc:
        return _error(str(exc))
    return 0


def cmd_agents_create(args: argparse.Namespace, client: JarvisClient) -> int:
    try:
        _print(
            client.create_agent(
                name=args.name,
                version=args.version,
                description=args.description,
                max_runtime_seconds=args.max_runtime_seconds,
                max_tool_calls=args.max_tool_calls,
            )
        )
    except JarvisClientError as exc:
        return _error(str(exc))
    return 0


def cmd_agents_get(args: argparse.Namespace, client: JarvisClient) -> int:
    try:
        _print(client.get_agent(args.agent_id))
    except JarvisClientError as exc:
        return _error(str(exc))
    return 0


def cmd_conversations_list(args: argparse.Namespace, client: JarvisClient) -> int:
    try:
        _print(client.list_conversations(limit=args.limit))
    except JarvisClientError as exc:
        return _error(str(exc))
    return 0


def cmd_conversations_create(args: argparse.Namespace, client: JarvisClient) -> int:
    try:
        _print(client.create_conversation(title=args.title))
    except JarvisClientError as exc:
        return _error(str(exc))
    return 0


def cmd_conversations_send(args: argparse.Namespace, client: JarvisClient) -> int:
    try:
        _print(
            client.send_message(
                conversation_id=args.conversation_id, content=args.content
            )
        )
    except JarvisClientError as exc:
        return _error(str(exc))
    return 0


def cmd_memory_list(args: argparse.Namespace, client: JarvisClient) -> int:
    try:
        _print(client.list_memory(memory_type=args.memory_type, limit=args.limit))
    except JarvisClientError as exc:
        return _error(str(exc))
    return 0


def cmd_memory_create(args: argparse.Namespace, client: JarvisClient) -> int:
    try:
        _print(
            client.create_memory(
                content=args.content,
                memory_type=args.memory_type,
                source=args.source,
                source_type=args.source_type,
                source_id=args.source_id,
                confidence=args.confidence,
            )
        )
    except JarvisClientError as exc:
        return _error(str(exc))
    return 0


def cmd_memory_search(args: argparse.Namespace, client: JarvisClient) -> int:
    try:
        _print(
            client.search_memory(
                query=args.query,
                memory_type=args.memory_type,
                limit=args.limit,
                threshold=args.threshold,
            )
        )
    except JarvisClientError as exc:
        return _error(str(exc))
    return 0


def cmd_memory_ingest(args: argparse.Namespace, client: JarvisClient) -> int:
    try:
        _print(
            client.ingest_document(
                content=args.content,
                source=args.source,
                source_type=args.source_type,
                source_id=args.source_id,
                memory_type=args.memory_type,
                confidence=args.confidence,
                chunk_size=args.chunk_size,
                overlap=args.overlap,
            )
        )
    except JarvisClientError as exc:
        return _error(str(exc))
    return 0


def cmd_approvals_list(args: argparse.Namespace, client: JarvisClient) -> int:
    try:
        _print(client.list_approvals(state=args.state, limit=args.limit))
    except JarvisClientError as exc:
        return _error(str(exc))
    return 0


def cmd_approvals_request(args: argparse.Namespace, client: JarvisClient) -> int:
    try:
        _print(
            client.request_approval(
                task_id=args.task_id, expires_in_minutes=args.expires_in_minutes
            )
        )
    except JarvisClientError as exc:
        return _error(str(exc))
    return 0


def cmd_approvals_approve(args: argparse.Namespace, client: JarvisClient) -> int:
    try:
        _print(client.approve_approval(approval_id=args.approval_id))
    except JarvisClientError as exc:
        return _error(str(exc))
    return 0


def cmd_approvals_deny(args: argparse.Namespace, client: JarvisClient) -> int:
    try:
        _print(client.deny_approval(approval_id=args.approval_id))
    except JarvisClientError as exc:
        return _error(str(exc))
    return 0


# --- argument parser --------------------------------------------------------


def _add_token_url(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--url",
        default=os.getenv("JARVIS_API_URL", DEFAULT_URL),
        help="JARVIS API base URL (default: JARVIS_API_URL or %(default)s)",
    )
    parser.add_argument(
        "--token",
        default=os.getenv("JARVIS_ACCESS_TOKEN"),
        help="Bearer access token (default: JARVIS_ACCESS_TOKEN)",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="jarvis-cli",
        description="JARVIS operator CLI — terminal client for the JARVIS API.",
    )
    _add_token_url(parser)
    sub = parser.add_subparsers(dest="command", required=True)

    def add(name: str, handler, setup) -> argparse.ArgumentParser:
        p = sub.add_parser(name, help=setup.__doc__)
        _add_token_url(p)
        setup(p)
        p.set_defaults(_handler=handler)
        return p

    # auth
    p = add(
        "login",
        cmd_login,
        lambda p: (
            p.add_argument("--username", required=True, help="Login username"),
            p.add_argument("--password", required=True, help="Login password"),
        ),
    )
    p.set_defaults(_handler=cmd_login)

    # me / health / ready / metrics
    for name, handler in (
        ("me", cmd_me),
        ("health", cmd_health),
        ("ready", cmd_ready),
        ("metrics", cmd_metrics),
    ):
        p = sub.add_parser(name, help=f"Show {name} information")
        _add_token_url(p)
        p.set_defaults(_handler=handler)

    # tasks
    p = sub.add_parser("tasks", help="Task operations")
    _add_token_url(p)
    tsub = p.add_subparsers(dest="subcommand", required=True)
    pl = tsub.add_parser("list", help="List tasks")
    _add_token_url(pl)
    pl.add_argument("--state", help="Filter by task state")
    pl.add_argument("--agent-id", help="Filter by agent id")
    pl.add_argument("--limit", type=int, default=100)
    pl.set_defaults(_handler=cmd_tasks_list)
    pc = tsub.add_parser("create", help="Create a task")
    _add_token_url(pc)
    pc.add_argument("--task-type", required=True)
    pc.add_argument("--risk-classification", default="low")
    pc.add_argument("--agent-id")
    pc.add_argument("--idempotency-key")
    pc.set_defaults(_handler=cmd_tasks_create)
    pg = tsub.add_parser("get", help="Get a task")
    _add_token_url(pg)
    pg.add_argument("task_id")
    pg.set_defaults(_handler=cmd_tasks_get)

    # agents
    p = sub.add_parser("agents", help="Agent operations")
    _add_token_url(p)
    asub = p.add_subparsers(dest="subcommand", required=True)
    pl = asub.add_parser("list", help="List agents")
    _add_token_url(pl)
    pl.add_argument("--is-active", action="store_true")
    pl.add_argument("--no-is-active", action="store_true")
    pl.add_argument("--limit", type=int, default=100)
    pl.set_defaults(_handler=cmd_agents_list)
    pc = asub.add_parser("create", help="Create an agent")
    _add_token_url(pc)
    pc.add_argument("--name", required=True)
    pc.add_argument("--version", default="1.0.0")
    pc.add_argument("--description")
    pc.add_argument("--max-runtime-seconds", type=int, default=300)
    pc.add_argument("--max-tool-calls", type=int, default=50)
    pc.set_defaults(_handler=cmd_agents_create)
    pg = asub.add_parser("get", help="Get an agent")
    _add_token_url(pg)
    pg.add_argument("agent_id")
    pg.set_defaults(_handler=cmd_agents_get)

    # conversations
    p = sub.add_parser("conversations", help="Conversation operations")
    _add_token_url(p)
    csub = p.add_subparsers(dest="subcommand", required=True)
    pl = csub.add_parser("list", help="List conversations")
    _add_token_url(pl)
    pl.add_argument("--limit", type=int, default=100)
    pl.set_defaults(_handler=cmd_conversations_list)
    pc = csub.add_parser("create", help="Create a conversation")
    _add_token_url(pc)
    pc.add_argument("--title")
    pc.set_defaults(_handler=cmd_conversations_create)
    ps = csub.add_parser("send", help="Send a message")
    _add_token_url(ps)
    ps.add_argument("conversation_id")
    ps.add_argument("content")
    ps.set_defaults(_handler=cmd_conversations_send)

    # memory
    p = sub.add_parser("memory", help="Memory operations")
    _add_token_url(p)
    msub = p.add_subparsers(dest="subcommand", required=True)
    pl = msub.add_parser("list", help="List memory items")
    _add_token_url(pl)
    pl.add_argument("--memory-type")
    pl.add_argument("--limit", type=int, default=100)
    pl.set_defaults(_handler=cmd_memory_list)
    pc = msub.add_parser("create", help="Create a memory item")
    _add_token_url(pc)
    pc.add_argument("content")
    pc.add_argument("--memory-type", default="conversation")
    pc.add_argument("--source")
    pc.add_argument("--source-type")
    pc.add_argument("--source-id")
    pc.add_argument("--confidence", type=int)
    pc.set_defaults(_handler=cmd_memory_create)
    ps = msub.add_parser("search", help="Semantic search memory")
    _add_token_url(ps)
    ps.add_argument("query")
    ps.add_argument("--memory-type")
    ps.add_argument("--limit", type=int, default=10)
    ps.add_argument("--threshold", type=float, default=0.0)
    ps.set_defaults(_handler=cmd_memory_search)
    pi = msub.add_parser("ingest", help="Ingest a document into memory")
    _add_token_url(pi)
    pi.add_argument("content")
    pi.add_argument("--source", required=True)
    pi.add_argument("--source-type", default="document")
    pi.add_argument("--source-id")
    pi.add_argument("--memory-type", default="semantic")
    pi.add_argument("--confidence", type=int, default=80)
    pi.add_argument("--chunk-size", type=int, default=1000)
    pi.add_argument("--overlap", type=int, default=200)
    pi.set_defaults(_handler=cmd_memory_ingest)

    # approvals
    p = sub.add_parser("approvals", help="Approval operations")
    _add_token_url(p)
    asub = p.add_subparsers(dest="subcommand", required=True)
    pl = asub.add_parser("list", help="List approval requests")
    _add_token_url(pl)
    pl.add_argument("--state")
    pl.add_argument("--limit", type=int, default=100)
    pl.set_defaults(_handler=cmd_approvals_list)
    pr = asub.add_parser("request", help="Request approval for a task")
    _add_token_url(pr)
    pr.add_argument("--task-id", required=True)
    pr.add_argument("--expires-in-minutes", type=int, default=60)
    pr.set_defaults(_handler=cmd_approvals_request)
    pa = asub.add_parser("approve", help="Approve a pending approval")
    _add_token_url(pa)
    pa.add_argument("approval_id")
    pa.set_defaults(_handler=cmd_approvals_approve)
    pd = asub.add_parser("deny", help="Deny a pending approval")
    _add_token_url(pd)
    pd.add_argument("approval_id")
    pd.set_defaults(_handler=cmd_approvals_deny)

    return parser


def main(argv: list[str] | None = None) -> int:
    """Entry point for the JARVIS operator CLI."""
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        # argparse exits on --help (code 0) or missing/invalid args (code 2).
        return int(exc.code or 0)
    url = getattr(args, "url", None)
    token = getattr(args, "token", None)
    client = _client(url, token)
    handler = getattr(args, "_handler", None)
    if handler is None:
        parser.print_help()
        return 1
    handler_fn = cast(Callable[[argparse.Namespace, JarvisClient], int], handler)
    try:
        return handler_fn(args, client)
    finally:
        client.close()


if __name__ == "__main__":
    sys.exit(main())
