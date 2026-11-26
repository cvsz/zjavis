# JARVIS

**Personal AI Operating System** — Local-first, multimodal, multi-agent platform.

## Status

**Phase 1 (Core Platform): COMPLETE**  
**Phase 2 (Model Gateway): COMPLETE**

JARVIS is a personal AI operating system providing governance-first AI capabilities: local-first AI model gateway, secure authentication and authorization, policy engine with execution-time policy decisions, approval workflows, tamper-evident audit logging, and PostgreSQL-backed persistence for conversations, tasks, agents, tasks, approvals, and memories.

## Features Implemented

### Core Platform (Phase 1)

- **Configuration management** (`src/jarvis/core/config.py`) — Type-safe settings with `JARVIS_`-prefixed environment variables, fail-closed secret key validation in production
- **Security** (`src/jarvis/core/security.py`) — PBKDF2-HMAC-SHA256 password hashing, HMAC-SHA256 JWT access tokens (no third-party JWT dependencies), capability-based permissions
- **Policy engine** (`src/jarvis/core/policy.py`) — ALLOW/DENY/REQUIRE_APPROVAL/REQUIRE_REAUTHENTICATION/OUT_OF_SCOPE decision engine
- **Approval service** (`src/jarvis/approval/__init__.py`) — Pending → granted/denied/expired lifecycle
- **Audit service** (`src/jarvis/audit/__init__.py`) — Tamper-evident event recording with tenant, actor, category, outcome tracking
- **Authentication** (`src/jarvis/auth/`) — Login, token issuance, current-user lookup, superuser checks
- **Database models** (`src/jarvis/db/models.py`) — 14 entities: organizations, users, tenants, roles, permissions, role_bindings, sessions, conversations, messages, memories, agents, tasks, approvals, audit_events
- **Database session** (`src/jarvis/db/session.py`) — SQLAlchemy async engine with connection pooling
- **Alembic migrations** (`alembic/versions/0001_initial_schema.py`) — Initial schema for all core entities

### AI Model Gateway (Phase 2)

- **Provider abstraction** (`src/jarvis/ai/gateway.py`) — Provider registry, model registry, routing policy, usage accounting
- **Provider adapters** (`src/jarvis/ai/provider.py`) — Local (no credentials), OpenAI-compatible API, Ollama
- **Conversation API** (`src/jarvis/api/conversations.py`) — Create/list conversations, add messages, AI chat with streaming support
- **Health endpoints** — `/health` (liveness), `/ready` (readiness with database check), `/metrics` (Prometheus)

### Infrastructure

- **Docker Compose** — PostgreSQL 16, Redis 7, JARVIS API
- **Dockerfile** — Non-root user, Python 3.12-alpine
- **Alembic migrations** — `0001_initial_schema`

## Getting Started

### Prerequisites

- Python 3.12+
- PostgreSQL 16+ (or Docker Compose)
- Redis 7+ (optional, for caching)

### Local Development

```bash
# Copy environment file
cp .env.example .env
# Edit .env with your settings (especially JARVIS_SECRET_KEY)

# Install dependencies
pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# Run the application
python -m jarvis

# Or with Docker Compose
docker-compose up --build
```

### API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `GET /health` | GET | Liveness probe |
| `GET /ready` | GET | Readiness probe (database check) |
| `GET /metrics` | GET | Prometheus text-format metrics |
| `POST /api/v1/auth/login` | POST | Authenticate, return access/refresh tokens |
| `GET /api/v1/auth/me` | GET | Current user profile |
| `POST /api/v1/auth/superuser-check` | POST | Verify superuser access |
| `POST /api/v1/conversations` | POST | Create conversation |
| `GET /api/v1/conversations` | GET | List conversations |
| `POST /api/v1/conversations/{id}/messages` | POST | Add message to conversation |
| `POST /api/v1/conversations/{id}/chat` | POST | Send message, get AI response |

## Security

- Passwords hashed with PBKDF2-HMAC-SHA256 (210,000 iterations)
- JWT access tokens signed with HMAC-SHA256
- Least-privilege capability-based permissions
- Secret redaction in logs
- No third-party JWT libraries (avoids known vulnerabilities)

Report vulnerabilities through [GitHub security](https://github.com/cvsz/zjavis/security) or the private channel documented in [SECURITY.md](SECURITY.md).

## Development

### Run Tests

```bash
pytest tests/
```

### Linting

```bash
ruff check src/ tests/ scripts/
mypy src/jarvis/
```

## Architecture

```
L0 Experience:       HTTP API (FastAPI)
L1 Identity:         JWT authentication, PBKDF2-HMAC-SHA256, RBAC permissions
L2 Gateway:          FastAPI route layer, health probes (/health, /ready)
L3 Intelligence:     Model gateway (provider abstraction, local adapter)
L4 Orchestration:    Task state model
L5 Capabilities:     Permission model
L6 Knowledge:        Memory model
L7 Data:             PostgreSQL (SQLAlchemy async, Alembic migrations)
L8 Events:           Audit event model (tamper-evident)
L9 Governance:       Policy engine, Approval service
L10 Operations:      Health/readiness probes, structured logging, secret redaction
```

## License

Review LICENSE copyright and choose a license before your first release. Template source retains the original copyright attribution where legally required.