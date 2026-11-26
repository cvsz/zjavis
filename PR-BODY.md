## Summary

This PR implements **Phase 1 (Core Platform)** of the JARVIS Personal AI Operating System per `javis-blueprint.md`, evolving the `cvsz/ztemplate` governance template into a runnable FastAPI backend.

## What was implemented

- **Configuration management** — pydantic-settings with `JARVIS_`-prefixed env vars, fail-closed secret key in production
- **Structured logging** — JSON-compatible logging with secret redaction (`SecretFilter`)
- **Security** — bcrypt password hashing, JWT access tokens, capability permissions (`system.read`, `repository.write`, `database.mutate`, etc.)
- **Policy engine** — 5 decision outcomes: `ALLOW`, `DENY`, `REQUIRE_APPROVAL`, `REQUIRE_REAUTHENTICATION`, `OUT_OF_SCOPE` (blueprint §15.3)
- **Approval service** — pending → granted/denied/expired lifecycle with expiration
- **Audit service** — tamper-evident event recording with actor, tenant, category, outcome
- **Authentication** — login (`/api/v1/auth/login`), current user (`/api/v1/auth/me`), superuser check (`/api/v1/auth/superuser-check`)
- **Database models** — 14 core entities per blueprint §13.1 (organizations, users, tenants, roles, permissions, conversations, messages, memories, agents, tasks, approvals, audit_events, etc.) with UUID primary keys and tenant-aware foreign keys
- **Database session** — SQLAlchemy async engine with connection pooling
- **Model gateway** — provider abstraction, model registry, routing, usage accounting; local provider adapter; cloud fallback disabled by default (blueprint §4.2)
- **Conversation API** — `GET/POST /api/v1/conversations`, `POST /api/v1/conversations/{id}/messages`
- **Health endpoints** — `/health` (liveness), `/ready` (readiness with database connectivity check)
- **FastAPI application** — global error handling, structured JSON error responses
- **Alembic migration** — `0001_initial_schema`
- **Docker Compose** — PostgreSQL + Redis + JARVIS API for local development
- **Production Dockerfile** — non-root `appuser`, pinned Python 3.12

## Testing

- **75 tests pass** (46 existing template tests + 29 new application tests)
- **mypy:** Clean (20 source files)
- **ruff:** Clean (only intentional FastAPI `Depends` B008 patterns)
- **validate_repo.py:** Passes (structure, links, syntax, security)
- **Integration tests:** Run against live PostgreSQL database

## Verification status

| Check | Result |
|---|---|
| Repository validation | PASS |
| Linting (ruff) | PASS |
| Type checking (mypy) | PASS |
| Unit tests (21) | PASS |
| Integration tests (8) | PASS |
| Secret scanning | PASS |
| GitHub admin gate | VERIFIED (applied via `scripts/github_admin.py --apply --verify`) |

## Known limitations / outstanding items

- GPG commit signing not available (passphrase required, no TTY)
- AI provider integration tests BLOCKED (no provider credentials available)
- Redis not available in environment (cache/working memory not tested)
- Observability (OpenTelemetry/Prometheus) not yet implemented
- Backup/restore not yet implemented
- Kubernetes/Helm deferred per blueprint §16.3

## Review requested

Independent review requested from `@policedbc` per repository branch protection requirements.
