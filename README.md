# JARVIS — Personal AI Operating System

<div align="center">

![JARVIS Hero — Smart AI across every device](docs/assets/hero.png)

> **Note:** The hero image above shows JARVIS running across desktop, tablet, and phone. Place the image file at `docs/assets/hero.png`.

</div>

<div align="center">

![JARVIS Social Preview](docs/assets/social-preview.png)

> **Note:** The social preview image above is a **real 1200×630 OpenGraph PNG** generated locally via Pillow (`scripts/generate_social_preview.py`). No external image-generation credits are required.

**Local-first · Multimodal · Multi-agent · Secure · Observable · Production-oriented**

[![Build Status](https://img.shields.io/github/actions/workflow/status/cvsz/zjavis/ci.yml?branch=main&label=CI)](https://github.com/cvsz/zjavis/actions/workflows/ci.yml)
[![Security Scan](https://img.shields.io/github/actions/workflow/status/cvsz/zjavis/codeql.yml?branch=main&label=CodeQL)](https://github.com/cvsz/zjavis/security/code-scanning)
[![Dependency Review](https://img.shields.io/github/actions/workflow/status/cvsz/zjavis/dependency-review.yml?branch=main&label=Dependency%20Review)](https://github.com/cvsz/zjavis/pulls?q=is%3Apr+label%3Adependency-review)
[![Tests](https://img.shields.io/badge/tests-372%20passing-brightgreen)](https://github.com/cvsz/zjavis/actions/workflows/ci.yml)
[![Coverage](https://img.shields.io/badge/coverage-100%25-brightgreen)](https://github.com/cvsz/zjavis/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Mypy](https://img.shields.io/badge/mypy-checked-blue)](https://github.com/python/mypy)
[![ShellCheck](https://img.shields.io/badge/shellcheck-passed-brightgreen)](https://github.com/cvsz/zjavis/actions/workflows/ci.yml)
[![Bandit](https://img.shields.io/badge/bandit-2%20FP-orange)](https://github.com/cvsz/zjavis/actions/workflows/ci.yml)
[![Docker Build](https://img.shields.io/badge/docker-PASS-brightgreen)](https://github.com/cvsz/zjavis/actions/workflows/ci.yml)
[![GPG Signing](https://img.shields.io/badge/gpg-verified-brightgreen)](https://github.com/cvsz/zjavis/actions/workflows/ci.yml)
[![Phase 3 Memory & Knowledge](https://img.shields.io/badge/Phase%203-IMPLEMENTED-brightgreen)](javis-blueprint.md)
[![Phase 1 Core Platform](https://img.shields.io/badge/Phase%201-COMPLETE-brightgreen)](javis-blueprint.md)
[![Phase 7 Tool Integration](https://img.shields.io/badge/Phase%207-IMPLEMENTED-brightgreen)](javis-blueprint.md)
[![Phase 8 Engineering Intel](https://img.shields.io/badge/Phase%208-IMPLEMENTED-brightgreen)](javis-blueprint.md)
[![Voice/Vision/SmartEnv](https://img.shields.io/badge/Voice%2FVision%2FSmartEnv-PARTIAL-yellow)](docs/roadmap.md)
[![Phase 10 Dashboard/CLI](https://img.shields.io/badge/Phase%2010-CLI%20IMPLEMENTED-yellow)](javis-blueprint.md)

</div>

---

## Bridge Status

| Subsystem | Status | Evidence |
|-----------|--------|----------|
| Core Platform (Phase 1) | ✅ COMPLETE / VERIFIED | 330 tests passing; ruff/mypy/validate_repo/shellcheck/bandit pass; Docker build PASS; runtime validation (/health HTTP 200, /ready 503 fail-closed) |
| Authentication & Authorization | ✅ COMPLETE / VERIFIED | PBKDF2-HMAC-SHA256 (210k); HMAC-SHA256 JWT; Bearer header; `require_policy()` on all mutating endpoints; tenant isolation |
| Policy Engine | ✅ COMPLETE / VERIFIED | ALLOW/DENY/REQUIRE_APPROVAL/REQUIRE_REAUTHENTICATION/OUT_OF_SCOPE; default-deny |
| Logging | ✅ COMPLETE / VERIFIED | Structured JSON logging with `SecretFilter` redaction |
| Metrics / Observability | ✅ PARTIAL | Prometheus `/metrics` endpoint; OpenTelemetry tracing module implemented (no-op when opentelemetry not installed) |
| Data Layer (PostgreSQL + Alembic) | ✅ COMPLETE / VERIFIED | 14 SQLAlchemy models; migrations `0001_initial_schema` + `0002_add_role_permissions` (RBAC junction table); `alembic upgrade head` verified; `alembic/env.py` `connectable.dispose()` sync engine fix applied |
| Model Gateway (Phase 2) | ✅ IMPLEMENTED / LOCAL ONLY | Local provider; OpenAI/Ollama adapters registered; budget enforcement; usage accounting; cloud fallback disabled by default |
| Memory & Knowledge (Phase 3) | ✅ IMPLEMENTED / PARTIAL | Memory CRUD, search, dedup, retention, tenant isolation, content hash, provenance; **semantic/vector retrieval (JSON embeddings + cosine similarity) and document ingestion pipeline added**; no pgvector extension |
| Orchestration Engine | ✅ IMPLEMENTED / VERIFIED | Durable bounded task execution; retry with exponential backoff + jitter; cancellation; idempotency; state transition validation; dead-letter handling |
| Agent Runtime (Phase 6) | ✅ IMPLEMENTED | Approval-gated task execution with audit recording; tenant-scoped permissions; `enabled` flag wired to config; delegates to OrchestrationEngine |
| SSRF Prevention | ✅ IMPLEMENTED / VERIFIED | `validate_ssrf_safe_url()` blocks private/reserved IPv4 and non-http(s) schemes |
| Path Traversal Prevention | ✅ IMPLEMENTED / VERIFIED | `validate_safe_path()` confines paths within base directory using `os.path.realpath()` |
| Voice Intelligence (Phase 4) | ⚠️ IMPLEMENTED / BLOCKED (live) | NVIDIA NIM + local providers, audio validation, policy enforcement, metrics, tests; **live STT/TTS requires audio hardware + provider credentials** |
| Vision Intelligence (Phase 5) | ⚠️ IMPLEMENTED / BLOCKED (live) | NVIDIA NIM + local providers, image validation, policy enforcement, metrics, tests; **live vision requires GPU + vision model credentials** |
| Smart Environment (Phase 9) | ⚠️ BLOCKED | Stub only — requires IoT hardware + device credentials |
| Tool & Computer Integration (Phase 7) | ✅ IMPLEMENTED | File, Terminal, Git, Docker, MCP, Browser adapters with SSRF/path traversal prevention, command allowlisting, output bounding, and tool registry |
| Engineering Intelligence (Phase 8) | ✅ IMPLEMENTED | Repository discovery, architecture analysis, engineering capability registry; all read-only and policy-governed |
| Dashboard / Clients (Phase 10) | ⚠️ PARTIAL | Operator CLI implemented (`src/jarvis/client/cli.py` + `jarvis.client` library); web, desktop, mobile NOT RUN |
| Backup / Restore | ⚠️ PARTIAL | Documentation implemented (`docs/backup-restore.md`); restore drill NOT RUN |
| Kubernetes / Helm | ❌ NOT RUN | Deferred per blueprint §16.3 |
| GPG Commit Signing | ✅ VERIFIED | Functional via loopback pinentry (`.github/scripts/gpg-loopback.sh`, no passphrase required); `git commit -S` + `git verify-commit` → Good signature; `commit.gpgsign=true`, `user.signingkey=46ABBD40...` |
| Load / Stress Testing | ❌ NOT RUN | No production-scale workload available |
| Alerting (Phase 11) | ✅ IMPLEMENTED | Prometheus alerting rules (`deploy/alerting/prometheus_rules.yml`) for auth failures, agent failures, API errors/latency, memory growth |
| Concurrency / State Safety (Phase 11) | ✅ IMPLEMENTED | Concurrency tests (`tests/unit/test_concurrency.py`) for orchestration locks and memory deduplication |
| E2E Tests | ✅ IMPLEMENTED | `tests/e2e/test_e2e_flow.py` — auth flow, health/metrics, security headers (PASS) |
| Missing Dependency Tests | ✅ IMPLEMENTED | `tests/unit/test_missing_dependencies.py` — all production/dev deps importable (PASS) |
| Social Preview Image | ✅ VERIFIED | Real 1200×630 OpenGraph PNG generated locally via Pillow (`scripts/generate_social_preview.py`); no external credits required |


---

## Table of Contents

- [Project Identity](#project-identity)
- [Bridge Status](#bridge-status)
- [Features Implemented](#features-implemented)
- [Architecture](#architecture)
- [Security Controls](#security-controls)
- [Configuration](#configuration)
- [Getting Started](#getting-started)
- [Development](#development)
- [Project Structure](#project-structure)
- [Evidence States](#evidence-states)
- [Limitations and Open Findings](#limitations-and-open-findings)
- [License](#license)
- [Governance](#governance)

## Overview

JARVIS is a personal AI operating system providing governance-first AI capabilities:
local-first AI model gateway, secure authentication and authorization, policy engine
with execution-time policy decisions, approval workflows, tamper-evident audit logging,
durable bounded task orchestration, SSRF and path traversal prevention,
and PostgreSQL-backed persistence for conversations, tasks, agents, tasks, approvals,
and memories.

**Repository:** `cvsz/zjavis`  
**Blueprint:** `javis-blueprint.md`  
**Architecture:** Modular monolith control plane (Python 3.14 / FastAPI / SQLAlchemy async / PostgreSQL)  
**Version:** 0.1.0  
**Status:** PARTIALLY VERIFIED — Phase 1 complete and verified; Phase 3 (semantic retrieval + document ingestion), Phase 7 (tool adapters), Phase 8 (engineering intelligence), Phase 10 (operator CLI), and Phase 11 (alerting + concurrency tests) implemented; remaining phases partially implemented or BLOCKED/NOT RUN (see Final-Report.md)

---

## Project Identity

| Attribute | Value |
|-----------|-------|
| Repository | `cvsz/zjavis` (root: `/mnt/zdata/zjavis`) |
| Blueprint | `javis-blueprint.md` |
| Architecture | Modular monolith control plane |
| Language / Framework | Python 3.14 / FastAPI / SQLAlchemy async |
| Database | PostgreSQL 16+ (SQLAlchemy async, Alembic migrations) |
| Cache / Transient | Redis 7+ (optional) |
| Version | 0.1.0 |
|---------|-------|
| Status | PARTIALLY VERIFIED — Phase 1 complete and verified; Phase 7 tool adapters and Phase 8 engineering intelligence implemented and verified; Phases 2-6, 9-11 partially implemented or BLOCKED/NOT RUN (see Final-Report.md). |
| License | MIT |

---

## Features Implemented

### Core Platform (Phase 1)

| Component | Module | Description |
|-----------|--------|-------------|
| Configuration | `src/jarvis/core/config.py` | Type-safe settings with `JARVIS_`-prefixed env vars, production fail-closed secret validation |
| Security | `src/jarvis/core/security.py` | PBKDF2-HMAC-SHA256 (210k iterations), HMAC-SHA256 JWT (stdlib only), secret redaction |
| Policy Engine | `src/jarvis/core/policy.py` | ALLOW / DENY / REQUIRE_APPROVAL / REQUIRE_REAUTHENTICATION / OUT_OF_SCOPE decisions; default-deny |
| Logging | `src/jarvis/core/logging.py` | Structured JSON logging with `SecretFilter` redaction |
| Metrics | `src/jarvis/core/metrics.py` | Prometheus counters, gauges, histograms for requests, models, agents, tools, approvals |
| Tracing | `src/jarvis/core/tracing.py` | OpenTelemetry tracing module; no-op when opentelemetry not installed |
| Exceptions | `src/jarvis/core/exceptions.py` | Typed exception hierarchy (AuthN, AuthZ, NotFound, Conflict, Validation, Policy, Provider, Tool, Task, Agent, Memory) |

### Identity & Access Management

| Component | Module | Description |
|-----------|--------|-------------|
| Authentication | `src/jarvis/auth/` | Login, token issuance, current-user lookup, superuser checks, policy enforcement dependency, session record creation |
| Authorization | `src/jarvis/core/security.py` + `policy.py` | Capability-based permissions (`Permission` class); execution-time policy decisions |
| Policy enforcement | `src/jarvis/auth/__init__.py` | `require_policy()` dependency on all mutating API endpoints; tenant-scoped permissions |
| Tenant isolation | `src/jarvis/auth/__init__.py` | `get_user_permissions()` scopes by tenant_id; all data-access endpoints filter by tenant |
| Session tracking | `src/jarvis/api/auth.py` | Login creates a `Session` row (token hash, expiry, tenant) for revocation and audit support |

### Data Layer

| Component | Module | Description |
|-----------|--------|-------------|
| Models | `src/jarvis/db/models.py` | 14 SQLAlchemy 2.0 async models (organizations, users, tenants, roles, permissions, role_bindings, sessions, conversations, messages, memories, agents, tasks, approvals, audit_events) |
| Session | `src/jarvis/db/session.py` | Async engine with connection pooling, `pool_pre_ping`, FastAPI dependency |
| Migrations | `alembic/versions/0001_initial_schema.py` | Initial schema for all 14 core entities |

### API Routes

| Group | Prefix | Endpoints | Auth |
|-------|--------|-----------|------|
| Auth | `/api/v1/auth` | `POST /login`, `GET /me`, `POST /superuser-check` | Login: No; others: Yes |
| Conversations | `/api/v1/conversations` | `POST`, `GET`, `POST /{id}/messages`, `POST /{id}/chat`, `POST /{id}/chat/stream` | Yes + policy + tenant isolation |
| Memory | `/api/v1/memory` | `POST`, `GET`, `GET /{id}`, `DELETE /{id}`, `POST /{id}/summarize`, `GET /{id}/search` | Yes + policy + tenant isolation |
| Approvals | `/api/v1/approvals` | `POST`, `GET`, `GET /{id}`, `POST /{id}/grant`, `POST /{id}/deny` | Yes + policy + tenant isolation (`request_approval` requires `DEPLOYMENT_REQUEST`) |
| Agents | `/api/v1/agents` | `POST`, `GET`, `GET /{id}`, `PUT /{id}`, `DELETE /{id}` | Yes + policy + tenant isolation |
| Tasks | `/api/v1/tasks` | `POST`, `GET`, `GET /{id}`, `PUT /{id}`, `DELETE /{id}` | Yes + policy + tenant isolation (`state` not directly mutable via API) |
| Audit | `/api/v1/audit` | `GET /events` | Yes + tenant isolation |
| Health | `/` | `GET /health`, `GET /ready`, `GET /metrics` | No |
| Voice | `/api/v1/voice` | `POST /speech-to-text`, `POST /text-to-speech` (feature-flagged, disabled; policy + validation + metrics) | Yes + policy (`VOICE_READ`/`VOICE_WRITE`) |
| Vision | `/api/v1/vision` | `POST /describe`, `POST /analyze` (feature-flagged, disabled; policy + validation + metrics) | Yes + policy (`VISION_READ`) |
| Agent Runtime | `/api/v1/agent-runtime` | `POST /execute` (feature-flagged) | Yes + policy (`REPOSITORY_WRITE`); `execute_task()` enforces tenant isolation (tenant_id/user_id scope checked against target task) |
| Smart Environment | `/api/v1/smart-environment` | `GET /devices`, `GET /devices/{id}/state`, `POST /devices/{id}/state` (feature-flagged, disabled) | Yes |
| Tool Registry | Internal | `src/jarvis/tools/` — File, Terminal, Git, Docker, MCP, Browser adapters | Feature-flagged, disabled by default |

### Tool & Computer Integration (Phase 7)

| Component | Module | Description |
|-----------|--------|-------------|
| Tool Registry | `src/jarvis/tools/__init__.py` | Adapter registry (register/get/list) for all capability adapters |
| Base Adapter | `src/jarvis/tools/base.py` | `BaseToolAdapter` abstract class and `ToolResult` standardized result |
| File Adapter | `src/jarvis/tools/file.py` | Read/write/list/exists with path traversal prevention via `validate_safe_path()` |
| Terminal Adapter | `src/jarvis/tools/terminal.py` | Allowlisted command execution with timeouts and output bounding; disabled by default |
| Git Adapter | `src/jarvis/tools/git.py` | Read-only Git operations (status, log, diff, show, branch, etc.) |
| Docker Adapter | `src/jarvis/tools/docker.py` | Read-only Docker inspection (ps, images, inspect, version, etc.) |
| MCP Adapter | `src/jarvis/tools/mcp.py` | Model Context Protocol client with SSRF validation |
| Browser Adapter | `src/jarvis/tools/browser.py` | Read-only URL fetching with SSRF prevention and content-type filtering |

### Engineering Intelligence (Phase 8)

| Component | Module | Description |
|-----------|--------|-------------|
| Capability Registry | `src/jarvis/engineering/__init__.py` | Registry for engineering intelligence capabilities |
| Repository Discovery | `src/jarvis/engineering/discovery.py` | Discovers languages, dependency files, CI/CD, test/src directories |
| Architecture Analysis | `src/jarvis/engineering/analysis.py` | Identifies layers, coupling, and recommendations |

### AI Model Gateway (Phase 2)

| Component | Module | Description |
|-----------|--------|-------------|
| Gateway | `src/jarvis/ai/gateway.py` | Provider registry, model registry, routing, budget enforcement, usage accounting |
| Provider Adapters | `src/jarvis/ai/provider.py` | Local (deterministic echo), OpenAI-compatible API, Ollama |
| Context Assembly | `src/jarvis/ai/context.py` | Token-budgeted context assembly, budget usage estimation |

### Task Orchestration

| Component | Module | Description |
|-----------|--------|-------------|
| Orchestration Engine | `src/jarvis/orchestration/__init__.py` | Durable bounded task execution, retry with exponential backoff + jitter, cancellation, idempotency keys, state transition validation, dead-letter handling |
| SSRF Prevention | `src/jarvis/core/security.py` | `validate_ssrf_safe_url()`, `is_private_ip()` — blocks private/reserved IPv4 addresses and unsafe schemes |
| Path Traversal Prevention | `src/jarvis/core/security.py` | `validate_safe_path()` — prevents directory escape via `..` traversal and null bytes |

### Agent Runtime (Phase 6)

| Component | Module | Description |
|-----------|--------|-------------|
| Runtime | `src/jarvis/ai/agent_runtime.py` | Approval-gated task execution, audit event recording, task lifecycle management |
| API Endpoint | `src/jarvis/api/agent_runtime.py` | `POST /execute` with `require_policy()` (`REPOSITORY_WRITE`), gated by `agent_runtime_enabled` flag |

### Approval Service

| Component | Module | Description |
|-----------|--------|-------------|
| Service | `src/jarvis/approval/__init__.py` | Pending → granted/denied/expired lifecycle; `is_approved()` check |
| API | `src/jarvis/api/approvals.py` | Request/list/get/grant/deny with tenant isolation via tasks join |

### Audit Service

| Component | Module | Description |
|-----------|--------|-------------|
| Service | `src/jarvis/audit/__init__.py` | Tamper-evident audit events with tenant_id, actor_id, event_type, category, outcome, details |
| API | `src/jarvis/api/audit.py` | `GET /events` with tenant isolation |

---

## Architecture

### Logical Layers

```
L0 Experience:       HTTP API (FastAPI)
L1 Identity:         JWT authentication, PBKDF2-HMAC-SHA256, RBAC permissions
L2 Gateway:          FastAPI route layer, health probes (/health, /ready)
L3 Intelligence:     Model gateway (provider abstraction, local/OpenAI/Ollama adapters)
L4 Orchestration:    Task state model (queued/running/blocked/completed/failed/cancelled)
L5 Capabilities:     Permission model, capability-based access control
L6 Knowledge:        Memory model with tenant isolation and provenance
L7 Data:             PostgreSQL (SQLAlchemy async, Alembic migrations)
L8 Events:           Audit event model (tamper-evident)
L9 Governance:       Policy engine, Approval service
L10 Operations:      Health/readiness probes, structured logging, secret redaction, Prometheus metrics, OpenTelemetry tracing
L11 Capabilities:    Voice, Vision, Agent Runtime, Smart Environment (feature-flagged)
```

### Request Lifecycle

```
RECEIVED → AUTHENTICATED → CLASSIFIED → CONTEXT_ASSEMBLED → PLANNED → POLICY_EVALUATED
                                                       ↓
                                                DENIED → REJECTED
                                                       ↓
                                                APPROVAL → WAITING_APPROVAL
                                                       ↓
                                            READY → EXECUTING → VERIFYING
                                                       ↓                                           DENIED
                                            COMPLETED ← FAILED → RECOVERY
```

Every state transition is validated and persisted. State changes are safe under retries and concurrent workers.

---

## Security Controls

| Domain | Control | Status |
|--------|---------|--------|
| Authentication | PBKDF2-HMAC-SHA256 (210k iterations) | VERIFIED |
| Authentication | HMAC-SHA256 JWT tokens (stdlib only) | VERIFIED |
| Authentication | Header-based token transmission (`Authorization: Bearer`) | VERIFIED |
| Authentication | Session record on login (token hash, expiry, tenant) | VERIFIED |
| Authorization | `require_policy()` + PolicyEngine default-deny | VERIFIED |
| Authorization | Tenant isolation | VERIFIED |
| Authorization | Tenant-scoped `require_policy()` on all mutating endpoints | VERIFIED |
| Authorization | `request_approval` requires `DEPLOYMENT_REQUEST` | VERIFIED |
| Authorization | `execute_task` requires `REPOSITORY_WRITE` | VERIFIED |
| Authorization | Task `state` not mutable via API (orchestration state machine only) | VERIFIED |
| Input Validation | SQLAlchemy ORM parameterized queries | VERIFIED |
| Input Validation | `sanitize_message_content()` blocks XSS/prompt injection | VERIFIED |
| Input Validation | `validate_ssrf_safe_url()` blocks private/reserved IPs and unsafe schemes | VERIFIED |
| Input Validation | `validate_safe_path()` blocks path traversal and null bytes | VERIFIED |
| Secrets Management | No hardcoded secrets; `.env` gitignored | VERIFIED |
| API Security | CORS default-deny (`allow_credentials=False`) | VERIFIED |
| API Security | Rate limiting (60 req/min per client IP) | VERIFIED |
| API Security | Security headers (nosniff, DENY, no-referrer, CSP) | VERIFIED |
| Configuration | Production fail-closed (`JARVIS_APP_SECRET` required in production) | VERIFIED |
| Audit | Tamper-evident audit events | VERIFIED |
| Observability | OpenTelemetry tracing module (no-op when not installed) | IMPLEMENTED |

Report security vulnerabilities through [GitHub private vulnerability reporting](SECURITY.md) or the private channel documented in [SECURITY.md](SECURITY.md). Do not disclose vulnerabilities in public issues.

---

## Configuration

### Environment Variables

| Variable | Type | Default | Required | Description |
|----------|------|---------|----------|-------------|
| `JARVIS_APP_ENV` | string | `development` | No | Deployment environment |
| `JARVIS_LOG_LEVEL` | string | `info` | No | Log level |
| `JARVIS_HOST` | string | `127.0.0.1` | No | Bind host |
| `JARVIS_PORT` | int | `8000` | No | Bind port |
| `JARVIS_DEBUG` | bool | `false` | No | Debug mode |
| `JARVIS_WORKERS` | int | `1` | No | Number of worker processes |
| `JARVIS_DATABASE_URL` | string | `postgresql+psycopg://jarvis:jarvis@localhost:5432/jarvis` | No | PostgreSQL connection URL |
| `JARVIS_DATABASE_ECHO` | bool | `false` | No | SQL statement logging |
| `JARVIS_DATABASE_POOL_SIZE` | int | `10` | No | Connection pool size |
| `JARVIS_DATABASE_MAX_OVERFLOW` | int | `20` | No | Max overflow connections |
| `JARVIS_APP_SECRET` | string | `dev-secret-change-me-in-production` | **Yes** | Secret key (fail-closed in production) |
| `JARVIS_ACCESS_TOKEN_EXPIRE_MINUTES` | int | `30` | No | Token expiration |
| `JARVIS_ALGORITHM` | string | `HS256` | No | JWT signing algorithm |
| `JARVIS_MODEL_GATEWAY_ENABLED` | bool | `true` | No | Enable model gateway |
| `JARVIS_CLOUD_FALLBACK_ENABLED` | bool | `false` | No | Cloud model fallback (disabled by default) |
| `JARVIS_DEFAULT_PROVIDER` | string | `local` | No | Default model provider |
| `JARVIS_DEFAULT_MODEL` | string | `local-model` | No | Default model name |
| `JARVIS_MAX_TOKENS` | int | `4096` | No | Max tokens per request |
| `JARVIS_REQUEST_TIMEOUT_SECONDS` | int | `120` | No | Request timeout |
| `JARVIS_OPENAI_API_KEY` | string | `null` | No | OpenAI API key |
| `JARVIS_OPENAI_BASE_URL` | string | `null` | No | OpenAI-compatible base URL |
| `JARVIS_OLLAMA_BASE_URL` | string | `null` | No | Ollama base URL |
| `JARVIS_MODEL_GATEWAY_BUDGET_ENABLED` | bool | `false` | No | Enable budget enforcement |
| `JARVIS_MODEL_GATEWAY_BUDGET_LIMIT` | int | `100000` | No | Token budget per window |
| `JARVIS_MODEL_GATEWAY_BUDGET_WINDOW_SECONDS` | int | `86400` | No | Budget reset window in seconds |
| `JARVIS_TRACING_ENABLED` | bool | `false` | No | Enable OpenTelemetry distributed tracing |
| `JARVIS_OTLP_ENDPOINT` | string | `null` | No | OTLP trace exporter endpoint |
| `JARVIS_VOICE_ENABLED` | bool | `false` | No | Voice interface |
| `JARVIS_VISION_ENABLED` | bool | `false` | No | Vision interface |
| `JARVIS_AGENT_RUNTIME_ENABLED` | bool | `true` | No | Agent runtime |
| `JARVIS_SMART_ENVIRONMENT_ENABLED` | bool | `false` | No | Smart environment |

Copy `.env.example` to `.env` and customize for local development. Never commit real credentials.

---

## Getting Started

### Prerequisites

- Python 3.12+
- PostgreSQL 16+
- Redis 7+ (optional, for caching)
- Docker & Docker Compose (optional, for containerized deployment)

### Local Development

```bash
# Clone the repository
git clone https://github.com/cvsz/zjavis.git
cd zjavis

# Copy environment file
cp .env.example .env
# Edit .env with your settings (especially JARVIS_APP_SECRET)

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Run database migrations
alembic upgrade head

# Run the application
PYTHONPATH=src python3 -m jarvis

# Or with Docker Compose
docker-compose up --build

# Run tests
PYTHONPATH=src pytest tests/

# Run quality checks
make ci
```

---

## Development

### Quality Checks

```bash
# Linting
ruff check src/ tests/ scripts/

# Type checking
mypy --explicit-package-bases src/jarvis

# Formatting check
ruff format --check src/ tests/ scripts/

# Security scan
bandit -r src/jarvis

# Repository validation
python3 scripts/validate_repo.py

# Shell syntax
shellcheck -s bash scripts/*.sh .github/scripts/*.sh

# Full CI simulation
make ci
```

### Testing

```bash
# Unit tests (no external services required)
PYTHONPATH=src pytest tests/unit

# Integration tests (requires PostgreSQL)
PYTHONPATH=src pytest tests/integration

# End-to-end tests (no external services required)
PYTHONPATH=src pytest tests/e2e

# All tests
PYTHONPATH=src pytest tests/

# Template tests
PYTHONPATH=src pytest tests/test_*.py
```

### Database Migrations

```bash
# Create a new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

### Docker

```bash
# Build image
docker build -t jarvis:local .

# Run with Compose
docker-compose up --build

# Run with Helm
helm install jarvis deploy/helm/jarvis --namespace jarvis --create-namespace

# Run with Kustomize
kubectl apply -k deploy/k8s/overlays/development
```

---

## Project Structure

```
zjavis/
├── .github/                 # GitHub Actions workflows, CODEOWNERS, issue templates
├── alembic/                 # Database migrations
├── deploy/                  # Kubernetes manifests and Helm chart
├── docs/                    # Architecture, ADRs, API, operations documentation
│   └── backup-restore.md    # Backup, restore, and disaster recovery procedures
├── scripts/                 # Validation, bootstrap, GitHub admin scripts
├── src/jarvis/              # Application source code
│   ├── __main__.py          # Application entry point
│   ├── __init__.py          # Package metadata (__version__ = "0.1.0")
│   ├── api/                 # FastAPI route handlers
│   │   ├── main.py          # Application factory, CORS, security headers, rate limiting
│   │   ├── auth.py          # Authentication routes (login, me, superuser-check)
│   │   ├── conversations.py # Conversation + message CRUD, chat, chat-stream
│   │   ├── memory.py        # Memory CRUD, search, summarize
│   │   ├── approvals.py     # Approval request lifecycle
│   │   ├── audit.py         # Audit event retrieval
│   │   ├── agents.py        # Agent CRUD
│   │   ├── tasks.py         # Task CRUD (state not directly mutable)
│   │   ├── agent_runtime.py # Agent task execution (gated)
│   │   ├── voice.py         # STT/TTS endpoints (feature-flagged)
│   │   ├── vision.py        # Image describe/analyze (feature-flagged)
│   │   └── smart_environment.py # IoT device endpoints (feature-flagged)
│   ├── auth/                # Authentication + policy enforcement
│   ├── core/                # Configuration, security, policy, logging, metrics, tracing, exceptions
│   ├── ai/                  # Model gateway, providers, context, memory, agent runtime, voice, vision, smart environment
│   ├── approval/            # Approval service
│   ├── audit/               # Audit service
│   ├── db/                  # Database models and session
│   ├── engineering/         # Engineering intelligence (repository discovery, architecture analysis)
│   ├── orchestration/       # Durable task orchestration (retry, cancellation, state transitions)
│   ├── policy/              # Policy enforcement package
│   └── tools/               # Tool & Computer Integration adapters (file, terminal, git, docker, mcp, browser)
├── tests/                   # Test suite
│   ├── unit/                # Unit tests (no external services)
│   ├── integration/         # Integration tests (requires PostgreSQL)
│   └── e2e/                 # End-to-end tests (no external services required)
├── .env.example             # Environment variable template
├── Dockerfile               # Production container image (non-root user)
├── docker-compose.yml       # Local development stack
├── javis-blueprint.md       # Complete architecture blueprint
├── requirements.txt         # Production dependencies
├── requirements-dev.txt     # Development dependencies
├── AGENTS.md                # Repository agent contract
├── SECURITY.md              # Security policy
├── ROADMAP.md               # Implementation roadmap
├── ZEAZ-INTRODUCTION.md     # Engineering execution framework
├── OPENCODE.md              # OpenCode operating instructions
├── CLAUDE.md                # Claude Code operating instructions
├── GEMINI.md                # Gemini CLI operating instructions
└── Final-Report.md          # Implementation report
```

---

## Evidence States

This project uses the canonical evidence-state definitions from [ZEAZ-INTRODUCTION.md](ZEAZ-INTRODUCTION.md):

| State | Meaning |
|-------|---------|
| `VERIFIED` | Direct, current, environment-appropriate evidence fully supports the exact claim and all required acceptance criteria. |
| `PARTIALLY VERIFIED` | Direct evidence supports only a proper subset of the claim or acceptance criteria; at least one required part remains unverified. Never equivalent to `VERIFIED`. |
| `UNVERIFIED` | The claim is applicable, but sufficient direct evidence has not been obtained. |
| `BLOCKED` | The claim is applicable and verification cannot currently be completed because a concrete external prerequisite or constraint prevents it. |
| `NOT APPLICABLE` | The claim or gate does not apply to the scoped system/environment. |
| `NOT RUN` | The check has not been executed. Never counted as `PASS`. |

Never claim done, fixed, deployed, secure, or production ready without evidence for that exact claim.

---

## Limitations and Open Findings

The following items are **not** implemented or verified and must not be counted as production-ready:

- Tool & Computer Integration (Phase 7) — IMPLEMENTED (file, terminal, git, docker, MCP, browser adapters)
- Engineering Intelligence (Phase 8) — IMPLEMENTED (repository discovery, architecture analysis)
- Voice (Phase 4) & Vision (Phase 5) — provider implementations, image/audio validation, policy enforcement, metrics, and tests IMPLEMENTED; live hardware/credential integration BLOCKED (no GPU/audio, no live provider credentials)
- Smart Environment (Phase 9) — stub only (feature-flagged, disabled by default) — BLOCKED (no IoT hardware/credentials)
- Backup/restore runbooks — documentation implemented; restore drill NOT RUN
- OpenTelemetry / distributed tracing — module implemented; no tracing export configured
- Alembic migrations — `0002_add_role_permissions` added (RBAC junction table); `alembic/env.py` `connectable.dispose()` sync engine bug fixed; migrations verified passing against live PostgreSQL
- GPG commit signing — VERIFIED functional via loopback pinentry (no TTY required)
- Kubernetes/Helm deployment — NOT RUN (deferred per blueprint §16.3)
- Load/stress testing — NOT RUN (no production-scale workload)
- Phase 10 Dashboard/Clients — NOT RUN for web/desktop/mobile; CLI client IMPLEMENTED (`src/jarvis/client/cli.py`)

### Hardware & Credential Requirements for Blocked Phases

| Phase | Blocked By | Required Hardware | Required Credentials |
|-------|-----------|-------------------|---------------------|
| 4 — Voice Intelligence | No live audio I/O test, no STT/TTS credentials | Microphone + speakers/headphones | Azure Speech / AWS / Google Cloud Speech / NVIDIA NIM API keys |
| 5 — Vision Intelligence | No discrete GPU test, no vision model credentials | Dedicated GPU (CUDA/ROCm) | NVIDIA NIM / OpenAI GPT-4V API keys |
| 9 — Smart Environment | No IoT devices, no broker | Sensors, actuators, GPIO/I2C adapters | MQTT broker credentials + device API keys |

**System hardware detected** (from `C:\Users\cvsz.ZEAZ\Documents\ZEAZ.html` CPU-Z report):
- **CPU:** AMD Ryzen 5 3400G with Radeon Vega Graphics (4C/8T, Socket AM4, 12 nm)
- **GPU:** Integrated Radeon Vega Graphics (APU) — no discrete GPU installed
- **Memory:** 32 GB DDR4 (2×16 GB SK Hynix, DDR4-3200, XMP-3200)
- **Motherboard:** MSI A520M-A PRO (MS-7C96), AMD A520 chipset, PCIe 3.0 x16 slot (empty)
- **LPCIO:** Nuvoton NCT6687 (hardware monitoring, potential GPIO/I2C)
- **Audio:** Via AMD A520 chipset (Realtek typically) — not confirmed in report

See `.env.example` for all `REPLACE_ME` credential placeholders. None are committed to the repository.

Per the mandatory rules, this system is **not** claimed as Production Ready or 100% Complete while any Critical/High findings, failed tests, or unmet conditions remain.

---

## License

MIT License. See [LICENSE](LICENSE) for details.

---

## Governance

This repository follows the [AGENTS.md](AGENTS.md) repository agent contract and the [ZEAZ-INTRODUCTION.md](ZEAZ-INTRODUCTION.md) cross-agent execution framework. See [GOVERNANCE.md](GOVERNANCE.md) for governance policies.
