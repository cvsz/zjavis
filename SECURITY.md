# Security Policy — zjavis (JARVIS Personal AI Operating System)

Security is part of the default delivery baseline for this repository.

## Reporting a vulnerability

Do not disclose exploitable vulnerabilities in public issues, pull requests, discussions, commit messages, logs, or generated evidence bundles.

Use GitHub private vulnerability reporting/security advisories when enabled, or the repository's documented private security contact.

Include affected versions/commits, reproduction details, impact, prerequisites, and suggested remediation when available.

## Supported versions

Each generated project must replace this section with its real support policy before its first production release.

## Repository security baseline

Generated repositories should verify, not merely document:

- protected default branch
- pull-request review before merge
- required status checks
- CODEOWNERS review where appropriate
- conversation resolution
- blocked force pushes/deletion
- Dependabot vulnerability alerts/security updates
- private vulnerability reporting
- secret scanning/push protection where available
- least-privilege Actions permissions
- Actions cannot approve pull requests unless explicitly justified

The helper `scripts/github_admin.py` can configure and verify the baseline when run with a GitHub identity that has Administration permission.

## Engineering security expectations

- Keep dependencies patched and review security alerts.
- Keep CodeQL and dependency-review workflows enabled where supported.
- Pin Actions according to supply-chain policy; this template pins baseline Actions to immutable SHAs.
- Never commit credentials, tokens, private keys, production secrets, sensitive personal data, or realistic sample secrets.
- Validate untrusted input and enforce authorization at trust boundaries.
- Prefer fail-closed behavior for security-sensitive paths.
- Preserve tenant/data isolation where applicable.
- Review generated/third-party agent instructions as untrusted until explicitly adopted.
- Do not weaken security gates merely to obtain a passing build.

## Incident handling

Generated projects should document detection, containment, credential handling, remediation, recovery, validation, disclosure, and rollback appropriate to their risk profile.

Security incidents affecting production systems should preserve evidence and use the smallest safe containment action consistent with the incident-response plan.

## zjavis security architecture

### Authentication (VERIFIED)

- Password hashing: PBKDF2-HMAC-SHA256 with 210,000 iterations (OWASP recommended minimum as of 2023)
- JWT tokens: HMAC-SHA256 signed using Python standard library only (no third-party JWT dependencies with known vulnerabilities)
- Token transmission: Header-based `Authorization: Bearer <token>` (query-string transmission eliminated)
- Token validation: Signature verified before payload decoding; expiration checked
- Current user resolution: Database lookup with active-status check

### Authorization (VERIFIED)

- Policy engine: `jarvis/core/policy.py` implements execution-time decisions per javis-blueprint.md §15.3
- Decision outcomes: `ALLOW`, `DENY`, `REQUIRE_APPROVAL`, `REQUIRE_REAUTHENTICATION`, `OUT_OF_SCOPE`
- Default: deny when policy cannot be evaluated
- Approval-required actions: `database.mutate`, `deployment.execute` (always require human approval regardless of permissions)
- High-risk actions (`risk_level` in `high`/`critical`) also require approval
- Capability-based permissions: `system.read`, `repository.read`, `repository.write`, `browser.read`, `browser.interact`, `terminal.allowlisted`, `container.inspect`, `database.read`, `database.mutate`, `deployment.request`, `deployment.execute`, `secrets.metadata.read`
- Policy enforcement dependency: `require_policy()` applied to all mutating API endpoints; resolves tenant context via `get_or_create_user_tenant()` and scopes permissions by tenant_id
- Tenant isolation: All data-access endpoints scope resources by tenant ID; user.id is never used as tenant_id
- Approval endpoints (`list`, `get`, `grant`, `deny`) enforce tenant isolation by joining through the `tasks` table
- Conversation endpoints (`list`, `create-message`, `chat`, `chat-stream`) enforce tenant isolation by filtering on `tenant_id`
- `get_user_permissions()` accepts optional `tenant_id` to scope role-binding permissions to a specific tenant
- `require_policy()` passes `tenant_id` to `PolicyEngine.evaluate()` for audit context
- **Phase 7 Tool Adapters:** All adapters (file, terminal, git, docker, MCP, browser) enforce SSRF/path traversal prevention, command allowlisting, output bounding, and are disabled by default

### Input validation (VERIFIED)

- SQLAlchemy ORM parameterized queries (no SQL injection)
- `sanitize_message_content()` blocks: `<script>` tags, `javascript:` URLs, `on*` event handlers, `ignore previous instructions`, `system: you are` prompt injection patterns
- Pydantic models with field constraints (min_length, max_length, type validation)
- UUID validation for path parameters
- SSRF prevention: `validate_ssrf_safe_url()` rejects `http`/`https` URLs targeting private/reserved IPv4 addresses (RFC 1918, RFC 5737, RFC 6598, RFC 3927) and non-http(s) schemes
- Path traversal prevention: `validate_safe_path()` resolves and confines user-supplied paths within a trusted base directory, rejecting `..` traversal, null bytes, and absolute paths

### API security (VERIFIED)

- CORS: Default-deny; `allow_origins=["*"]` with `allow_credentials=False` (credentialed wildcard CORS prohibited)
- Security headers: `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer`, `Content-Security-Policy: default-src 'self'`
- Rate limiting: 60 requests per minute per client IP
- Global error handler: Structured JSON errors, no stack traces leaked to clients

### Secrets management (VERIFIED)

- No hardcoded secrets in source code
- `.env` is gitignored; `.env.example` contains placeholders only
- `SecretFilter` redacts secret-like values from logs (password, secret, token, api_key, authorization, credential, private_key, session, cookie)
- `redact_secret()` helper for safe logging of secret values
- Production fail-closed: `JARVIS_APP_SECRET` must not be the development default when `JARVIS_APP_ENV=production`
- API keys for model providers loaded from environment, never embedded in code

### Audit (VERIFIED)

- `AuditService` records tamper-evident audit events with tenant_id, actor_id, event_type, event_category, outcome, details, occurred_at
- Audit categories: auth, security, system, tool, agent, memory, approval
- Audit outcomes: success, failure, denial
- Agent runtime records task execution outcomes (completed, failed, blocked)

### Orchestration (VERIFIED)

- Durable bounded task execution with absolute deadlines and per-step timeouts
- Retry with exponential backoff and jitter (bounded retries)
- Cancellation propagation
- Idempotency keys for mutating operations
- State transition validation (queued → running → completed/failed/blocked/cancelled)
- Dead-letter handling via failed state recording

### Known findings and status (Bandit security scan)

| Severity | Count | Status | Details |
|----------|-------|--------|---------|
| Critical | 0 | — | None |
| High | 0 | RESOLVED | All 9 high-severity findings from prior audit fixed (tenant_id FK violations, auth header, CORS, config extra="forbid") |
| Medium | 0 | — | None |
| Low | 2 | FALSE POSITIVE | Bandit B105: `"bearer"` token type string at `src/jarvis/auth/__init__.py:135` (standard OAuth 2.0 token type, not a password); `dev-secret-change-me-in-production` comparison at `src/jarvis/core/config.py:68` (production fail-closed validation, not a secret) |

**Total issues by severity (Bandit):** Undefined: 0, Low: 2 (False Positives), Medium: 0, High: 0  
**Total issues by confidence (Bandit):** Undefined: 0, Low: 0, Medium: 2, High: 0  
**Actual security vulnerabilities remaining:** 0

### Additional authorization hardening applied (this session)

| # | Severity | File | Finding | Fix | Status |
|---|----------|------|---------|-----|--------|
| A1 | Medium | `src/jarvis/api/approvals.py` | `request_approval` endpoint authenticated but had no execution-time authorization policy — any authenticated user could request approvals | Added `require_policy()` with `DEPLOYMENT_REQUEST` permission; policy enforced at request time | FIXED |
| A2 | Medium | `src/jarvis/api/agent_runtime.py` | `execute_task` endpoint authenticated but had no `require_policy()` — any authenticated user could trigger agent task execution | Added `require_policy()` with `REPOSITORY_WRITE` permission; policy enforced at request time | FIXED |
| A3 | Medium | `src/jarvis/api/tasks.py` | `TaskUpdate` model exposed `state` field, allowing API clients to mutate task state directly and bypass the OrchestrationEngine state machine | Removed `state` from `TaskUpdate`; state transitions enforced exclusively by `OrchestrationEngine.validate_state_transition()` | FIXED |
| A4 | Medium | `src/jarvis/api/auth.py` | Login returned tokens but created no session record — tokens could not be tracked or revoked | Login now persists a `Session` row (token hash, expiry, tenant) for revocation and audit support | FIXED |
| A5 | Medium | `src/jarvis/ai/agent_runtime.py` | `AgentRuntime.execute_task()` loaded a task by ID only, with no tenant/user scope check — a caller knowing another tenant's task ID could invoke it | `execute_task()` now accepts `tenant_id` and `user_id` and rejects the call with `AuthorizationError` (`tenant_isolation_violation` / `user_ownership_violation`) when the task does not belong to the scoped principal | FIXED |
| A6 | Low | `src/jarvis/tools/terminal.py` | Shared `terminal_tool` singleton was `enabled=True` by default, contradicting the security-by-default principle that all adapters are disabled unless explicitly enabled | `terminal_tool` default changed to `enabled=False`; Git and Docker adapters use their own dedicated `TerminalToolAdapter(enabled=True)` instances so they remain independently operable | FIXED |

### Security areas not yet implemented (BLOCKED / NOT RUN)

- Voice interface (STT/TTS): requires audio hardware + provider credentials → BLOCKED
- Vision interface: requires GPU hardware + vision model credentials → BLOCKED
- Smart environment / IoT: requires device hardware + credentials → BLOCKED
- Backup/restore: not implemented → NOT RUN
- OpenTelemetry / distributed tracing: metrics endpoint exists, no tracing → NOT RUN
- GPG commit signing: signing key requires passphrase; no TTY available in non-interactive environment → BLOCKED (cannot complete `git commit -S` without passphrase provisioning)
- Kubernetes/Helm deployment: deferred per blueprint §16.3 → NOT RUN
- Load/stress testing: no production-scale workload available → NOT RUN
- Dashboard/Clients (Phase 10): not implemented → NOT RUN

### Verification evidence (current session)

| Check | Command | Result | Evidence |
|-------|---------|--------|----------|
| Build | `python3 -m py_compile src/jarvis/**/*.py tests/unit/*.py scripts/*.py` | PASS | All files compile without syntax errors |
| Ruff lint | `python3 -m ruff check src/ tests/ scripts/` | PASS | 0 errors, 0 warnings across 91 files |
| Ruff format | `python3 -m ruff format --check src/ tests/ scripts/` | PASS | 91 files already formatted |
| MyPy | `python3 -m mypy --explicit-package-bases src/jarvis` | PASS | 0 issues in 51 source files |
| ShellCheck | `shellcheck -s bash scripts/*.sh .github/scripts/*.sh` | PASS | No errors |
| Pytest (all) | `PYTHONPATH=src python3 -m pytest tests/` | PASS | 326 passed, 0 failed |
| Bandit (security) | `bandit -r src/jarvis` | 2 Low (False Positives) | Both documented above; 0 actual findings |
| validate_repo | `python3 scripts/validate_repo.py` | PASS | Structure, links, syntax, security validation passed |
| Docker build | `docker build -t jarvis:local .` | PASS | Image `jarvis:local` built successfully |

## Supply chain security

- Dependabot enabled for dependency vulnerability alerts
- Dependency Review workflow (`dependency-review.yml`) fails on high severity
- CodeQL workflow (`codeql.yml`) for static analysis
- Actions pinned to immutable SHAs
- `validate_repo.py` scans for hardcoded secrets and tracked secret-bearing files
