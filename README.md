# JARVIS — Personal AI Operating System

<div align="center">

![JARVIS Social Preview — BLOCKED: social-preview.png could not be generated (external image-generation credits unavailable). Placeholder only; not a product claim.](https://placehold.co/1200x630/0f172a/38bdf8?text=JARVIS+Social+Preview+BLOCKED)

**Local-first · Multimodal · Multi-agent · Secure · Observable · Production-oriented**

[![Build Status](https://img.shields.io/github/actions/workflow/status/cvsz/zjavis/ci.yml?branch=main&label=CI)](https://github.com/cvsz/zjavis/actions/workflows/ci.yml)
[![Security Scan](https://img.shields.io/github/actions/workflow/status/cvsz/zjavis/codeql.yml?branch=main&label=CodeQL)](https://github.com/cvsz/zjavis/security/code-scanning)
[![Dependency Review](https://img.shields.io/github/actions/workflow/status/cvsz/zjavis/dependency-review.yml?branch=main&label=Dependency%20Review)](https://github.com/cvsz/zjavis/pulls?q=is%3Apr+label%3Adependency-review)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Mypy](https://img.shields.io/badge/mypy-checked-blue)](https://github.com/python/mypy)

</div>

---

## Bridge Status

| Subsystem | Status | Evidence |
|-----------|--------|----------|
| Core Platform (Phase 1) | ✅ COMPLETE | 205 tests passing (159 unit + 6 integration + 46 template + orchestration) |
| Model Gateway (Phase 2) | ✅ COMPLETE | Local provider, OpenAI-compatible, Ollama adapters; routing, budget, usage accounting |
| Voice Intelligence (Phase 4) | ⚠️ STUB | Feature-flagged, disabled by default; LocalVoiceProvider returns error without audio hardware/credentials |
| Vision Intelligence (Phase 5) | ⚠️ STUB | Feature-flagged, disabled by default; LocalVisionProvider returns error without GPU/model credentials |
| Agent Runtime (Phase 6) | ✅ COMPLETE | Approval-gated task execution, audit event recording, task lifecycle management |
| Orchestration Engine | ✅ COMPLETE | Bounded execution: timeout, retry+exponential backoff+jitter, CancellationToken, idempotency, dead-letter (10 unit tests) |
| Smart Environment (Phase 9) | ⚠️ STUB | Feature-flagged, disabled by default; requires IoT hardware + device credentials |
| Observability | ✅ PARTIAL | Prometheus metrics endpoint (/metrics); no distributed tracing |
| Backup / Restore | ❌ NOT IMPLEMENTED | Runbooks not implemented |
| Kubernetes / Helm | ✅ AVAILABLE | Manifests and chart provided |

---

## Overview

JARVIS is a personal AI operating system providing governance-first AI capabilities:
local-first AI model gateway, secure authentication and authorization, policy engine
with execution-time policy decisions, approval workflows, tamper-evident audit logging,
and PostgreSQL-backed persistence for conversations, tasks, agents, tasks, approvals,
and memories.

**Repository:** `cvsz/zjavis`  
**Blueprint:** `javis-blueprint.md`  
**Architecture:** Modular monolith control plane (Python 3.14 / FastAPI / SQLAlchemy async)

---

## Features Implemented

### Core Platform (Phase 1)

| Component | Module | Description |
|-----------|--------|-------------|
| Configuration | `src/jarvis/core/config.py` | Type-safe settings with `JARVIS_`-prefixed env vars, production fail-closed secret validation |
| Security | `src/jarvis/core/security.py` | PBKDF2-HMAC-SHA256 (210k iterations), HMAC-SHA256 JWT (stdlib only), secret redaction |
| Policy Engine | `src/jarvis/core/policy.py` | ALLOW / DENY / REQUIRE_APPROVAL / REQUIRE_REAUTHENTICATION / OUT_OF_SCOPE decisions |
| Logging | `src/jarvis/core/logging.py` | Structured JSON logging with secret redaction filter |
| Metrics | `src/jarvis/core/metrics.py` | Prometheus counters, gauges, histograms for requests, models, agents, tools, approvals |
| Exceptions | `src/jarvis/core/exceptions.py` | Typed exception hierarchy (AuthN, AuthZ, NotFound, Conflict, Validation, Policy, Provider, Tool, Task, Agent, Memory) |

### Identity & Access Management

| Component | Module | Description |
|-----------|--------|-------------|
| Authentication | `src/jarvis/auth/` | Login, token issuance, current-user lookup, superuser checks |
| Authorization | `src/jarvis/core/security.py` | Capability-based permissions (`Permission` class) |
| Policy | `src/jarvis/core/policy.py` | Execution-time policy decisions with default-deny |

### Data Layer

| Component | Module | Description |
|-----------|--------|-------------|
| Models | `src/jarvis/db/models.py` | 14 SQLAlchemy 2.0 async models (organizations, users, tenants, roles, permissions, role_bindings, sessions, conversations, messages, memories, agents, tasks, approvals, audit_events) |
| Session | `src/jarvis/db/session.py` | Async engine with connection pooling, `pool_pre_ping`, FastAPI dependency |
| Migrations | `alembic/versions/0001_initial_schema.py` | Initial schema for all 14 core entities |

### API Routes

| Group | Prefix | Endpoints |
|-------|--------|-----------|
| Auth | `/api/v1/auth` | `POST /login`, `GET /me`, `POST /superuser-check` |
| Conversations | `/api/v1/conversations` | `POST`, `GET`, `POST /{id}/messages`, `POST /{id}/chat`, `POST /{id}/chat/stream` |
| Memory | `/api/v1/memory` | `POST`, `GET`, `GET /{id}`, `DELETE /{id}`, `POST /{id}/summarize`, `GET /{id}/search` |
| Approvals | `/api/v1/approvals` | `POST`, `GET`, `GET /{id}`, `POST /{id}/grant`, `POST /{id}/deny` |
| Agents | `/api/v1/agents` | `POST`, `GET`, `GET /{id}`, `PUT /{id}`, `DELETE /{id}` |
| Tasks | `/api/v1/tasks` | `POST`, `GET`, `GET /{id}`, `PUT /{id}`, `DELETE /{id}` |
| Audit | `/api/v1/audit` | `GET /events` |
| Health | `/` | `GET /health`, `GET /ready`, `GET /metrics` |
| Voice | `/api/v1/voice` | `POST /speech-to-text`, `POST /text-to-speech` (feature-flagged) |
| Vision | `/api/v1/vision` | `POST /describe`, `POST /analyze` (feature-flagged) |
| Agent Runtime | `/api/v1/agent-runtime` | `POST /execute` (feature-flagged) |
| Smart Environment | `/api/v1/smart-environment` | `GET /devices`, `GET /devices/{id}/state`, `POST /devices/{id}/state` (feature-flagged) |

### AI Model Gateway (Phase 2)

| Component | Module | Description |
|-----------|--------|-------------|
| Gateway | `src/jarvis/ai/gateway.py` | Provider registry, model registry, routing, budget enforcement, usage accounting |
| Provider Adapters | `src/jarvis/ai/provider.py` | Local (deterministic echo), OpenAI-compatible API, Ollama |
| Context Assembly | `src/jarvis/ai/context.py` | Token-budgeted context assembly, budget usage estimation |

### Agent Runtime (Phase 6)

| Component | Module | Description |
|-----------|--------|-------------|
| Runtime | `src/jarvis/ai/agent_runtime.py` | Approval-gated task execution, audit event recording, task lifecycle management |

---

## Architecture

### Logical Layers

```
L0 Experience:       HTTP API (FastAPI) + WebSocket-ready
L1 Identity:         JWT authentication, PBKDF2-HMAC-SHA256, RBAC permissions
L2 Gateway:          FastAPI route layer, health probes (/health, /ready)
L3 Intelligence:     Model gateway (provider abstraction, local/OpenAI/Ollama adapters)
L4 Orchestration:    Task state model (queued/running/blocked/completed/failed/cancelled)
L5 Capabilities:     Permission model, capability-based access control
L6 Knowledge:        Memory model with tenant isolation and provenance
L7 Data:             PostgreSQL (SQLAlchemy async, Alembic migrations)
L8 Events:           Audit event model (tamper-evident)
L9 Governance:       Policy engine, Approval service
L10 Operations:      Health/readiness probes, structured logging, secret redaction, Prometheus metrics
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

### API Endpoints

| Endpoint | Method | Description | Auth Required |
|----------|--------|-------------|---------------|
| `GET /health` | GET | Liveness probe | No |
| `GET /ready` | GET | Readiness probe (DB check) | No |
| `GET /metrics` | GET | Prometheus text-format metrics | No |
| `POST /api/v1/auth/login` | POST | Authenticate, return access/refresh tokens | No |
| `GET /api/v1/auth/me` | GET | Current user profile | Yes (Bearer) |
| `POST /api/v1/auth/superuser-check` | POST | Verify superuser access | Yes (Bearer) |
| `POST /api/v1/conversations` | POST | Create conversation | Yes |
| `GET /api/v1/conversations` | GET | List conversations | Yes |
| `POST /api/v1/conversations/{id}/messages` | POST | Add message | Yes |
| `POST /api/v1/conversations/{id}/chat` | POST | Send message, get AI response | Yes |
| `POST /api/v1/conversations/{id}/chat/stream` | POST | Streaming AI response | Yes |
| `POST /api/v1/memory` | POST | Create memory item | Yes |
| `GET /api/v1/memory` | GET | List memories | Yes |
| `GET /api/v1/memory/{id}` | GET | Get memory by ID | Yes |
| `DELETE /api/v1/memory/{id}` | DELETE | Soft-delete memory | Yes |
| `POST /api/v1/approvals` | POST | Request approval | Yes |
| `GET /api/v1/approvals` | GET | List approvals | Yes |
| `POST /api/v1/approvals/{id}/grant` | POST | Grant approval | Yes |
| `POST /api/v1/approvals/{id}/deny` | POST | Deny approval | Yes |
| `POST /api/v1/agents` | POST | Create agent | Yes |
| `GET /api/v1/agents` | GET | List agents | Yes |
| `POST /api/v1/tasks` | POST | Create task | Yes |
| `GET /api/v1/tasks` | GET | List tasks | Yes |
| `GET /api/v1/audit/events` | GET | List audit events | Yes |

---

## Security

### Controls

- **Password hashing:** PBKDF2-HMAC-SHA256 with 210,000 iterations (OWASP recommended minimum)
- **JWT tokens:** HMAC-SHA256 signed using Python standard library only (no third-party JWT dependencies with known vulnerabilities)
- **Authorization:** Capability-based permissions with execution-time policy decisions (default-deny)
- **Input validation:** SQLAlchemy ORM parameterized queries (no SQL injection); message content sanitization blocks XSS and prompt injection patterns
- **CORS:** Default-deny configuration; `allow_credentials=False` when wildcard origins are used
- **Security headers:** `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer`, `Content-Security-Policy: default-src 'self'`
- **Rate limiting:** 60 requests per minute per client IP
- **Secret redaction:** Secret-like values redacted from logs via `SecretFilter`
- **Secrets management:** No hardcoded secrets; `.env` is gitignored; `.env.example` contains placeholders only
- **Tenant isolation:** All data-access endpoints scope resources by tenant ID
- **Production fail-closed:** `JARVIS_APP_SECRET` must be set when `JARVIS_APP_ENV=production`

### Reporting Vulnerabilities

Report security vulnerabilities through [GitHub Security Advisories](https://github.com/cvsz/zjavis/security/advisories) or the private channel documented in [SECURITY.md](SECURITY.md). Do not disclose vulnerabilities in public issues.

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
| `JARVIS_MODEL_GATEWAY_BUDGET_WINDOW_SECONDS` | int | `86400` | No | Budget reset window |
| `JARVIS_VOICE_ENABLED` | bool | `false` | No | Voice interface |
| `JARVIS_VISION_ENABLED` | bool | `false` | No | Vision interface |
| `JARVIS_AGENT_RUNTIME_ENABLED` | bool | `true` | No | Agent runtime |
| `JARVIS_SMART_ENVIRONMENT_ENABLED` | bool | `false` | No | Smart environment |

Copy `.env.example` to `.env` and customize for local development. Never commit real credentials.

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
├── scripts/                 # Validation, bootstrap, GitHub admin scripts
├── src/jarvis/              # Application source code
│   ├── __main__.py          # Application entry point
│   ├── api/                 # FastAPI route handlers
│   ├── auth/                # Authentication module
│   ├── core/                # Configuration, security, policy, logging, metrics, exceptions
│   ├── ai/                  # Model gateway, providers, context, memory, agent runtime, voice, vision, smart environment
│   ├── approval/            # Approval service
│   ├── audit/               # Audit service
│   ├── db/                  # Database models and session
│   ├── orchestration/       # Task orchestration layer
│   └── policy/              # Policy enforcement package
├── tests/                   # Test suite
│   ├── unit/                # Unit tests (no external services)
│   └── integration/         # Integration tests (requires PostgreSQL)
├── .env.example             # Environment variable template
├── Dockerfile               # Production container image (non-root user)
├── docker-compose.yml       # Local development stack
├── javis-blueprint.md       # Complete architecture blueprint
├── requirements.txt         # Production dependencies
├── requirements-dev.txt     # Development dependencies
└── Final-Report.md          # Implementation report
```

---

## License

MIT License. See [LICENSE](LICENSE) for details.

---

## Governance

This repository follows the [AGENTS.md](AGENTS.md) repository agent contract and the [ZEAZ-INTRODUCTION.md](ZEAZ-INTRODUCTION.md) cross-agent execution framework. See [GOVERNANCE.md](GOVERNANCE.md) for governance policies.
