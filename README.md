# JARVIS

**Personal AI Operating System** — Local-first, multimodal, multi-agent platform.

## Status

**Phase 1 (Core Platform): COMPLETE**  
**Phase 2 (Model Gateway + Memory): COMPLETE**

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
- **Memory service** (`src/jarvis/ai/memory.py`) — Document ingestion with chunking/deduplication, hybrid retrieval, retention, deletion
- **Memory API** (`src/jarvis/api/memory.py`) — CRUD, search, conversation summarization, conversation search
- **Health endpoints** — `/health` (liveness), `/ready` (readiness with database check), `/metrics` (Prometheus)

### Management APIs

- **Approvals API** (`src/jarvis/api/approvals.py`) — Request, list, get, grant, deny approval lifecycle
- **Agents API** (`src/jarvis/api/agents.py`) — CRUD for agent definitions
- **Tasks API** (`src/jarvis/api/tasks.py`) — CRUD for task execution units
- **Audit API** (`src/jarvis/api/audit.py`) — List audit events with filtering

### AI Capabilities (feature-flagged)

- **Voice API** (`src/jarvis/api/voice.py`, `src/jarvis/ai/voice.py`) — Speech-to-text and text-to-speech provider abstraction (`JARVIS_VOICE_ENABLED`)
- **Vision API** (`src/jarvis/api/vision.py`, `src/jarvis/ai/vision.py`) — Image describe and analyze provider abstraction (`JARVIS_VISION_ENABLED`)
- **Agent Runtime** (`src/jarvis/api/agent_runtime.py`, `src/jarvis/ai/agent_runtime.py`) — Autonomous agent task execution with approval gates (`JARVIS_AGENT_RUNTIME_ENABLED`)
- **Smart Environment** (`src/jarvis/api/smart_environment.py`, `src/jarvis/ai/smart_environment.py`) — IoT device management provider abstraction (`JARVIS_SMART_ENVIRONMENT_ENABLED`)

### Infrastructure

- **Docker Compose** — PostgreSQL 16, Redis 7, JARVIS API
- **Dockerfile** — Non-root user, Python 3.12-alpine
- **Alembic migrations** — `0001_initial_schema`
- **Kubernetes manifests** (`deploy/k8s/`) — Namespace, ConfigMap, Secret, Deployment, Service with kustomize overlays
- **Helm chart** (`deploy/helm/jarvis/`) — Full Helm chart with templates, values, and helpers

### CI & Security

- **OpenSSF Scorecard** — Weekly security supply chain analysis
- **Trivy container scanning** — HIGH/CRITICAL vulnerability detection
- **SBOM + SLSA provenance** — SPDX JSON SBOM and provenance attestation
- **Release signing and attestation** — Signed release artifacts with provenance

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

# Or with Helm
helm install jarvis deploy/helm/jarvis --namespace jarvis --create-namespace
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
| `POST /api/v1/conversations/{id}/chat/stream` | POST | Streaming AI response |
| `POST /api/v1/memory` | POST | Create memory item |
| `GET /api/v1/memory` | GET | List memories |
| `GET /api/v1/memory/{id}` | GET | Get memory by ID |
| `DELETE /api/v1/memory/{id}` | DELETE | Soft-delete memory |
| `POST /api/v1/memory/{conversation_id}/summarize` | POST | Summarize conversation to memory |
| `GET /api/v1/memory/{conversation_id}/search` | GET | Search memory within conversation |
| `POST /api/v1/approvals` | POST | Request approval |
| `GET /api/v1/approvals` | GET | List approvals |
| `GET /api/v1/approvals/{id}` | GET | Get approval by ID |
| `POST /api/v1/approvals/{id}/grant` | POST | Grant approval |
| `POST /api/v1/approvals/{id}/deny` | POST | Deny approval |
| `POST /api/v1/agents` | POST | Create agent |
| `GET /api/v1/agents` | GET | List agents |
| `GET /api/v1/agents/{id}` | GET | Get agent by ID |
| `PUT /api/v1/agents/{id}` | PUT | Update agent |
| `DELETE /api/v1/agents/{id}` | DELETE | Delete agent |
| `POST /api/v1/tasks` | POST | Create task |
| `GET /api/v1/tasks` | GET | List tasks |
| `GET /api/v1/tasks/{id}` | GET | Get task by ID |
| `PUT /api/v1/tasks/{id}` | PUT | Update task |
| `DELETE /api/v1/tasks/{id}` | DELETE | Delete task |
| `GET /api/v1/audit/events` | GET | List audit events |
| `POST /api/v1/voice/speech-to-text` | POST | Speech to text (voice_enabled) |
| `POST /api/v1/voice/text-to-speech` | POST | Text to speech (voice_enabled) |
| `POST /api/v1/vision/describe` | POST | Describe image (vision_enabled) |
| `POST /api/v1/vision/analyze` | POST | Analyze image (vision_enabled) |
| `POST /api/v1/agent-runtime/execute` | POST | Execute task via agent runtime (agent_runtime_enabled) |
| `GET /api/v1/smart-environment/devices` | GET | List IoT devices (smart_environment_enabled) |
| `GET /api/v1/smart-environment/devices/{id}/state` | GET | Get device state (smart_environment_enabled) |
| `POST /api/v1/smart-environment/devices/{id}/state` | POST | Set device state (smart_environment_enabled) |

## Security

- Passwords hashed with PBKDF2-HMAC-SHA256 (210,000 iterations)
- JWT access tokens signed with HMAC-SHA256
- Least-privilege capability-based permissions
- Secret redaction in logs
- No third-party JWT libraries (avoids known vulnerabilities)
- Feature flags gate experimental AI capabilities (disabled by default)

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

### Deployment

```bash
# Kubernetes (kustomize)
kubectl apply -k deploy/k8s/overlays/development

# Helm
helm install jarvis deploy/helm/jarvis --namespace jarvis --create-namespace
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
L11 Capabilities:    Voice, Vision, Agent Runtime, Smart Environment (feature-flagged)
```

## License

MIT License
