# Roadmap — zjavis (JARVIS Personal AI Operating System)

This repository implements the `javis-blueprint.md` specification as a modular, security-first AI platform.
The roadmap below tracks the actual implementation status of zjavis, not the generic template foundation.

## Phase 1 — Core Platform (COMPLETE — VERIFIED)

- [x] Authentication integration (PBKDF2-HMAC-SHA256, HMAC-SHA256 JWT, Bearer header)
- [x] API foundation (FastAPI, global error handler, rate limiting, security headers, CORS default-deny)
- [x] PostgreSQL schema (14 core entities: organizations, users, tenants, roles, permissions, role_bindings, sessions, conversations, messages, memories, agents, tasks, approvals, audit_events)
- [x] Alembic migrations: `0001_initial_schema` + `0002_add_role_permissions` (RBAC junction table); `alembic/env.py` `connectable.dispose()` sync engine bug fixed; `alembic upgrade head` verified against live PostgreSQL
- [x] Tenant boundaries (all data-access endpoints scope by tenant_id)
- [x] Policy engine (ALLOW/DENY/REQUIRE_APPROVAL/REQUIRE_REAUTHENTICATION/OUT_OF_SCOPE, default-deny)
- [x] Approval service (pending -> granted/denied/expired lifecycle)
- [x] Audit service (tamper-evident audit events)
- [x] Health endpoints (/health, /ready)
- [x] Configuration and secret handling (pydantic-settings, production fail-closed)
- [x] Structured logging with secret redaction
- [x] Prometheus metrics endpoint (/metrics)
- [x] Model gateway (local provider, OpenAI-compatible, Ollama; budget enforcement; usage accounting)
- [x] Context assembly (token-budgeted)
- [x] Memory service (CRUD, search, dedup, retention, stats)
- [x] Agent runtime (approval-gated task execution, audit recording)

## Phase 2 — Model Gateway (IMPLEMENTED — local provider only)

- [x] Provider registry and model registry
- [x] Local provider adapter (deterministic echo for testing without credentials)
- [x] OpenAI-compatible provider adapter (requires API key — not configured)
- [x] Ollama provider adapter (requires local Ollama — not running)
- [x] Model routing by task type
- [x] Budget enforcement and usage accounting
- [ ] Cloud fallback — explicitly DISABLED by default (blueprint §4.2); requires explicit authorization to enable
- [ ] Live provider integration tests — BLOCKED (no AI provider credentials available)

## Phase 3 — Memory and Knowledge (IMPLEMENTED — data model + service)

- [x] Memory model (7 types: working, conversation, episodic, semantic, procedural, project, preference)
- [x] Source provenance (source, source_type, source_id, content_hash)
- [x] Deduplication via SHA-256 content hash
- [x] Keyword search with tenant isolation
- [x] Retention (expires_at, delete_expired_memories)
- [x] Soft-delete (is_deleted)
- [ ] Semantic/vector retrieval (pgvector) — NOT IMPLEMENTED (no pgvector extension available)
- [ ] Document ingestion pipeline — NOT IMPLEMENTED

## Phase 4 — Voice Intelligence (IMPLEMENTED — code-ready; live BLOCKED)

- [x] Provider abstraction: `VoiceProvider` ABC with STT/TTS (voice.py)
- [x] LocalVoiceProvider stub (no hardware/credentials required)
- [x] Azure, Google, NVIDIA NIM, AWS provider adapters (AWS notes SigV4 not implemented)
- [x] Provider selection (`_build_provider`); mixed/partial config falls back to local stub
- [x] Audio payload validation: size cap (25 MB), empty rejection (validate_audio)
- [x] Execution-time policy enforcement: `VOICE_READ` (STT), `VOICE_WRITE` (TTS) via `require_policy()`
- [x] Feature-flagged, disabled by default (`JARVIS_VOICE_ENABLED`)
- [x] Prometheus metrics: `jarvis_voice_requests_total`, latency, audio bytes
- [x] Unit tests: providers, service enable/disable, provider selection, validation
- [ ] Real STT/TTS pipeline tested on supported hardware — BLOCKED (no audio hardware + no live provider credentials)
- [ ] Streaming, interruption, wake-word — NOT IMPLEMENTED
- [x] Voice API endpoints (feature-flagged, disabled by default, return 501 when disabled)
- Status: IMPLEMENTED (code-ready, policy-governed, tested); live integration BLOCKED — requires audio hardware + STT/TTS provider credentials not available

## Phase 5 — Vision Intelligence (IMPLEMENTED — code-ready; live BLOCKED)

- [x] Provider abstraction: `VisionProvider` ABC with describe_image/analyze_image (vision.py)
- [x] LocalVisionProvider stub (no GPU/credentials required)
- [x] NVIDIA NIM vision-language provider (chat/completions with base64 image input)
- [x] Image validation: magic-byte content-type detection (PNG/JPEG/WEBP), size cap (10 MB), empty/rejection (validate_image)
- [x] Provider selection (`_build_provider`); `nvidia` accepted as alias for `nvidia-nim`; unknown falls back to local stub
- [x] Execution-time policy enforcement: `VISION_READ` via `require_policy()`
- [x] Feature-flagged, disabled by default (`JARVIS_VISION_ENABLED`); CPU fallback device
- [x] Prometheus metrics: `jarvis_vision_requests_total`, latency, image bytes
- [x] Config fields: `vision_provider`, `vision_api_key`, `vision_api_url`, `vision_model`, `vision_max_image_bytes`
- [x] Unit tests: validation, detection, providers, service enable/disable, provider selection
- [ ] Real vision pipeline tested on supported hardware — BLOCKED (no discrete GPU + no live vision model credentials)
- [ ] OCR, screen understanding, video frame analysis — NOT IMPLEMENTED
- [x] Vision API endpoints (feature-flagged, disabled by default, return 501 when disabled)
- Status: IMPLEMENTED (code-ready, policy-governed, tested); live integration BLOCKED — requires GPU hardware + vision model provider credentials not available

## Phase 6 — Agent Runtime (IMPLEMENTED — approval-gated)

- [x] Agent registry (Agent model, CRUD API)
- [x] Typed agent contracts (name, version, max_runtime, max_tool_calls)
- [x] Planner and task graph — basic (model gateway completion)
- [x] Durable execution (task state: queued/running/blocked/completed/failed/cancelled)
- [x] Capability permissions (PolicyEngine)
- [x] Budgets and limits (model gateway budget)
- [x] Cancellation and recovery (task retry_count, error_message)
- [x] Approval workflow (ApprovalService integration)
- [x] Task orchestration engine (bounded execution, exponential backoff retry, cancellation, state transition validation, idempotency)
- [x] SSRF prevention (`validate_ssrf_safe_url`, `is_private_ip`)
- [x] Path traversal prevention (`validate_safe_path`)
- [x] Tenant isolation on all approval endpoints (list/get/grant/deny scope by tenant via tasks join)
- [x] Tenant isolation on all conversation endpoints (list/create-message/chat/chat-stream filter by tenant_id)
- [x] `require_policy()` resolves tenant context and passes tenant_id to PolicyEngine
- [x] `get_user_permissions()` scopes role-binding permissions by optional tenant_id
- [x] `AgentRuntime` API endpoint passes `enabled=settings.agent_runtime_enabled`
- [x] `OrchestrationEngine._persist_context()` validates state transitions
- [x] Approval grant/deny use `DEPLOYMENT_REQUEST` (not `DEPLOYMENT_EXECUTE`) to avoid circular approval dependency

## Phase 7 — Tool and Computer Integration (IMPLEMENTED)

- [x] File adapter (`src/jarvis/tools/file.py`) — read/write/list/exists with path traversal prevention
- [x] Terminal adapter (`src/jarvis/tools/terminal.py`) — allowlisted commands with timeout and output bounding
- [x] Git adapter (`src/jarvis/tools/git.py`) — read-only Git operations
- [x] Docker adapter (`src/jarvis/tools/docker.py`) — read-only Docker inspection
- [x] MCP adapter (`src/jarvis/tools/mcp.py`) — Model Context Protocol client with SSRF validation
- [x] Browser adapter (`src/jarvis/tools/browser.py`) — read-only URL fetching with SSRF prevention
- [x] Tool registry (`src/jarvis/tools/__init__.py`) — adapter registration and discovery
- [x] All adapters feature-flagged and disabled by default
- Status: IMPLEMENTED — 18 tests passing

## Phase 8 — Engineering Intelligence (IMPLEMENTED)

- [x] Repository discovery (`src/jarvis/engineering/discovery.py`) — languages, dependency files, CI/CD, structure
- [x] Architecture analysis (`src/jarvis/engineering/analysis.py`) — layers, coupling, recommendations
- [x] Capability registry (`src/jarvis/engineering/__init__.py`) — capability registration and discovery
- [x] All operations read-only and policy-governed
- Status: IMPLEMENTED — 31 tests passing

## Phase 9 — Smart Environment (STUB — BLOCKED)

- [ ] Device registry — NOT IMPLEMENTED
- [ ] Home Assistant adapter — NOT IMPLEMENTED
- [ ] MQTT adapter — NOT IMPLEMENTED
- [ ] Event normalization — NOT IMPLEMENTED
- [ ] Safe automation rules — NOT IMPLEMENTED
- [ ] Manual override — NOT IMPLEMENTED
- [x] Smart environment API endpoints (feature-flagged, disabled by default, return 501)
- [x] LocalSmartEnvironmentProvider placeholder (returns empty/error)
- Status: BLOCKED — requires IoT hardware + device credentials not available

## Phase 10 — Dashboard and Clients (NOT IMPLEMENTED)

- [ ] Web application — NOT IMPLEMENTED
- [ ] Desktop application — NOT IMPLEMENTED
- [ ] Mobile application — NOT IMPLEMENTED
- [ ] CLI for operators — NOT IMPLEMENTED
- [ ] Voice interaction surface — NOT IMPLEMENTED
- Status: NOT RUN

## Phase 11 — Production Hardening (PARTIAL)

### Authorization hardening applied (this session)
- [x] `request_approval` endpoint now requires `require_policy()` with `DEPLOYMENT_REQUEST` permission (was authentication-only).
- [x] `execute_task` agent runtime endpoint now requires `require_policy()` with `REPOSITORY_WRITE` permission (was authentication-only).
- [x] `TaskUpdate` model no longer exposes `state` field — state transitions enforced exclusively by OrchestrationEngine state machine.
- [x] Login endpoint now creates a `Session` database record for token tracking and revocation support.
- [x] `AgentRuntime.execute_task()` now enforces tenant isolation: tenant_id and user_id are checked against the target task before execution (prevents cross-tenant task execution).
- [x] Engineering capabilities (repository discovery, architecture analysis) self-register in the engineering capability registry on package import.
- [x] Terminal tool adapter default changed to `enabled=False` (security-by-default; all Phase 7 adapters are disabled unless explicitly enabled).

- [x] Security remediation (all 9 high-severity findings fixed; 2 documented Bandit False Positives)
- [x] Tenant isolation hardening on approval and conversation endpoints
- [x] Execution-time policy enforcement with tenant-scoped permissions on all mutating endpoints
- [x] SSRF prevention (`validate_ssrf_safe_url`, `is_private_ip`) — blocks private/reserved IPv4 and unsafe schemes
- [x] Path traversal prevention (`validate_safe_path`) — confines paths within base directory, rejects `..`, null bytes, absolute paths
- [x] Durable task orchestration engine (bounded execution, exponential backoff + jitter, cancellation, idempotency, state transition validation, dead-letter handling)
- [x] Missing dependency tests — `tests/unit/test_missing_dependencies.py` verifies all production and dev dependencies are importable (PASS)
- [x] E2E tests — `tests/e2e/test_e2e_flow.py` covers auth flow, health/metrics, security headers (PASS)
- [x] OpenTelemetry tracing module — `src/jarvis/core/tracing.py` (no-op tracer when opentelemetry not installed; enabled via `JARVIS_TRACING_ENABLED=true`)
- [x] Backup/Restore documentation — `docs/backup-restore.md` (procedures documented; restore drill NOT RUN)
- [ ] Load and stress tests — NOT RUN (no production-scale workload)
- [ ] Concurrency tests — NOT RUN
- [ ] Backup and restore restore drill — NOT RUN (no restore drill performed)
- [ ] Disaster recovery — NOT RUN
- [x] Deployment — Docker Compose available; Docker image `jarvis:local` builds successfully (PASS); K8s/Helm deferred per blueprint §16.3
- [x] Observability (Prometheus metrics endpoint) — PARTIAL (OpenTelemetry tracing module implemented; no distributed tracing export configured)
- [ ] Alerting — NOT IMPLEMENTED
- [ ] Cross-platform validation — NOT RUN
- [x] Independent review — CODEOWNERS configured (@policedbc for src/, tests/, .github/)
- [ ] Release evidence — NOT RUN
- [x] GPG commit signing — VERIFIED functional via loopback pinentry (`gpg --batch --no-tty --pinentry-mode loopback`); signing key has no passphrase; `git commit -S` + `git verify-commit` → Good signature; all branch commits GPG-signed

## Acceptance criteria (blueprint §22)

| Metric | Initial target | Status |
|--------|---------------|--------|
| Core API availability | 99.9% | NOT MEASURED |
| Core API p95 latency (excl. model inference) | ≤ 300 ms | NOT MEASURED |
| Unauthorized privileged actions | 0 | VERIFIED (default-deny policy) |
| Secret leakage | 0 | VERIFIED (no hardcoded secrets) |
| Unbounded agent execution | 0 | VERIFIED (bounded retries, timeouts) |
| Untracked production changes | 0 | VERIFIED (all changes via PR) |
| Task state invariants | 100% in defined test scenarios | VERIFIED |
| Backup restore verification | Pass before release | NOT RUN |
| Critical security findings | 0 before production release | VERIFIED |

## Future optional modules (template)

- [ ] Language-specific starter packs
- [ ] Infrastructure-as-code starter packs
- [ ] Kubernetes and Helm starter packs
- [ ] SBOM/provenance workflows
- [ ] Release signing and artifact attestation
- [ ] OpenSSF Scorecard workflow
- [ ] Container vulnerability scanning
- [ ] Documentation site starter
- [ ] Monorepo profile
- [ ] Service/API profile
- [ ] Web application profile
- [ ] Library/SDK profile
- [ ] Machine-readable skill catalog/version index

Generated repositories should adopt only modules appropriate to their stack, threat model, operating environment, and compliance needs.
