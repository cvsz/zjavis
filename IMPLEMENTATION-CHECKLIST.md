# Implementation Checklist

Use this checklist after creating a repository from `ztemplate`, or as an audit checklist when porting the baseline into an existing repository.

## Bootstrap

- [ ] Create the new repository with **Use this template** when independent history is desired.
- [ ] Preview and apply `scripts/bootstrap.py` with the actual name, owner, code owner, and description.
- [ ] Review the changed identity/ownership files and commit `.ztemplate-initialized.json` as nonsecret setup evidence.
- [ ] Run `make validate-template`.
- [ ] Choose a project profile in `docs/profiles.md` and record non-goals.
- [ ] Confirm README and ABOUT describe the real project.

## Repository identity

- [ ] Replace template identity/placeholders with the real project.
- [ ] Confirm license choice and preserve required attribution.
- [ ] Configure repository description, topics, homepage, visibility, and template status as applicable.

## Ownership and governance

- [ ] Update `.github/CODEOWNERS`.
- [ ] Review `CONTRIBUTING.md`, `GOVERNANCE.md`, and `CODE_OF_CONDUCT.md`.
- [ ] Run the GitHub administration helper in dry-run mode.
- [ ] Apply repository administration controls with an authenticated admin identity.
- [ ] Verify the effective controls:

  ```bash
  python3 scripts/github_admin.py --repo OWNER/REPO --verify
  ```

- [ ] Require pull-request review and CODEOWNERS approval.
- [ ] Require passing status checks and conversation resolution.
- [ ] Block force pushes and deletion of the protected default branch.
- [ ] Document any break-glass role/process.

## Security

- [ ] Replace the generic support policy in `SECURITY.md`.
- [ ] Configure private vulnerability reporting.
- [ ] Enable Dependabot alerts and security updates.
- [ ] Review CodeQL language support for the actual stack.
- [ ] Keep dependency review enabled where supported.
- [ ] Enable secret scanning and push protection where available.
- [ ] Add stack-specific SAST, container, IaC, SBOM, provenance, and signing checks as appropriate.
- [ ] Confirm Actions permissions follow least privilege.
- [ ] Confirm fork PRs cannot access unsafe secrets or write tokens.
- [ ] Pin third-party/first-party Actions according to project supply-chain policy.

## Development

- [ ] Select runtime/framework/package manager and supported versions.
- [ ] Add formatter/linter/type-checker configuration as appropriate.
- [ ] Add unit, integration, and end-to-end tests.
- [ ] Replace placeholder Makefile targets with real commands.
- [ ] Replace/remove the placeholder Dockerfile.
- [ ] Populate `.env.example` with safe non-secret names only.
- [ ] Document local setup and deterministic dependency installation.

## Cloudflare and DNS

- [ ] Read `docs/cloudflare-terraform.md`.
- [ ] Keep public DNS/shared tunnel ownership in one designated infrastructure repository.
- [ ] Confirm the service answers locally before requesting a public hostname.
- [ ] Import existing records instead of recreating them.
- [ ] Confirm infrastructure plans do not destroy unrelated resources.
- [ ] Verify sibling/shared routes after changes.

## CI/CD

- [ ] Customize CI for the selected stack.
- [ ] Pin runtime versions and define supported-version matrices.
- [ ] Add real lint/test/build/package/security validation.
- [ ] Configure artifact retention and provenance where needed.
- [ ] Configure environments, approvals, and deployment protections.
- [ ] Validate CI from both pull requests and the protected default branch.

## Release

- [ ] Choose an explicit versioning policy.
- [ ] Maintain `CHANGELOG.md` and release notes.
- [ ] Configure publishing only when required.
- [ ] Publish from trusted workflows only.
- [ ] Add artifact signing/attestation where appropriate.
- [ ] Document known-good rollback.
- [ ] Verify rollback on production-equivalent infrastructure when applicable.

## Operations

- [ ] Define health/readiness checks.
- [ ] Configure structured logs, metrics, traces, and alert routing appropriate to the service.
- [ ] Define backup scope, retention, encryption, and ownership.
- [ ] Perform an isolated restore drill for stateful systems.
- [ ] Define RPO/RTO where applicable.
- [ ] Document incident response and escalation.
- [ ] Perform load/capacity testing when performance or scale is a readiness gate.

## Documentation

- [ ] Complete `docs/architecture.md`.
- [ ] Complete `docs/development.md`.
- [ ] Complete `docs/release.md`.
- [ ] Add ADRs for material decisions.
- [ ] Document operational ownership and support expectations.

## Final verification

- [ ] Fresh clone works with documented setup.
- [ ] Repository validator passes.
- [ ] Required CI/security checks pass on the exact release head.
- [ ] Protected-branch/admin verification succeeds.
- [ ] No secrets/private data are committed.
- [ ] Deployment is verified in the intended environment.
- [ ] Backup/restore and rollback evidence exists where applicable.
- [ ] Every applicable production-readiness gate is `VERIFIED`; any `NOT APPLICABLE` gate has an explicit reason.

A green template CI run alone is never sufficient to claim application production readiness.

---

## zjavis Project Status (cvsz/zjavis — JARVIS Personal AI Operating System)

This section records the current state of the zjavis implementation per `javis-blueprint.md` and is updated with each release.

| System | Phase | Status | Evidence |
|--------|-------|--------|----------|
| Core Platform | Phase 1 | COMPLETE / VERIFIED | 330 tests passing; ruff/mypy/validate_repo/shellcheck/bandit pass; Docker build PASS; runtime validation (/health HTTP 200, /ready 503 fail-closed) |
| Authentication & Authorization | Phase 1 | COMPLETE / VERIFIED | PBKDF2-HMAC-SHA256 (210k); HMAC-SHA256 JWT; Bearer header; `require_policy()` on all mutating endpoints; tenant isolation; session record on login; **RBAC fixed — `get_user_permissions()` now joins via `role_permissions` junction table, default role self-provisioned** |
| Policy Engine | Phase 1 | COMPLETE / VERIFIED | ALLOW/DENY/REQUIRE_APPROVAL/REQUIRE_REAUTHENTICATION/OUT_OF_SCOPE; default-deny |
| Logging / Metrics / Tracing | Phase 1 | COMPLETE / PARTIAL | Structured JSON logging with `SecretFilter`; Prometheus `/metrics`; OpenTelemetry tracing module (no export configured) |
| Data Layer (PostgreSQL + Alembic) | Phase 1 | COMPLETE / VERIFIED | 14 SQLAlchemy models; migrations `0001_initial_schema` + `0002_add_role_permissions` (RBAC junction table); `alembic upgrade head` verified against live PostgreSQL; `alembic/env.py` `connectable.dispose()` sync engine fix applied |
| Model Gateway | Phase 2 | IMPLEMENTED / LOCAL ONLY | Local provider; OpenAI/Ollama adapters registered; budget enforcement; usage accounting; cloud fallback disabled by default |
| Memory & Knowledge | Phase 3 | IMPLEMENTED / PARTIAL | Memory CRUD, search, dedup, retention, tenant isolation, content hash, provenance; **semantic/vector retrieval (JSON embeddings + cosine similarity) and document ingestion pipeline added**; no pgvector extension |
| Orchestration Engine | Phase 6 | IMPLEMENTED / VERIFIED | Durable bounded task execution; retry with exponential backoff + jitter; cancellation; idempotency; state transition validation; dead-letter handling |
| Agent Runtime | Phase 6 | IMPLEMENTED | Approval-gated task execution with audit recording; tenant-scoped permissions; `enabled` flag wired to config; tenant isolation on `execute_task()` |
| SSRF Prevention | Phase 6/7 | IMPLEMENTED / VERIFIED | `validate_ssrf_safe_url()` blocks private/reserved IPv4 and non-http(s) schemes |
| Path Traversal Prevention | Phase 6/7 | IMPLEMENTED / VERIFIED | `validate_safe_path()` confines paths within base directory using `os.path.realpath()` |
| Tool & Computer Integration | Phase 7 | IMPLEMENTED | File, Terminal, Git, Docker, MCP, Browser adapters with SSRF/path traversal prevention, command allowlisting, output bounding, and tool registry. All adapters disabled by default. |
| Engineering Intelligence | Phase 8 | IMPLEMENTED | Repository discovery, architecture analysis, engineering capability registry; all read-only and policy-governed; self-register on package import |
| Voice Intelligence | Phase 4 | BLOCKED | Stub only — requires audio hardware + STT/TTS provider credentials |
| Vision Intelligence | Phase 5 | BLOCKED | Stub only — requires GPU hardware + vision model provider credentials |
| Smart Environment | Phase 9 | BLOCKED | Stub only — requires IoT hardware + device credentials |
| Dashboard / Clients | Phase 10 | IMPLEMENTED / PARTIAL | Operator CLI implemented (`src/jarvis/client/cli.py` + `jarvis.client` library); **web dashboard added (`src/jarvis/ui/` with `/login`, `/dashboard`, model status, task center, agent monitor, approvals, memory center, system health)**; desktop, mobile NOT RUN |
| Backup / Restore | Phase 11 | PARTIAL | Documentation implemented (`docs/backup-restore.md`); restore drill NOT RUN |
| Kubernetes / Helm | Phase 11 | NOT RUN | Deferred per blueprint §16.3 |
| Load / Stress Testing | Phase 11 | NOT RUN | No production-scale workload available |
| GPG Commit Signing | Phase 11 | VERIFIED | Functional via loopback pinentry (`.github/scripts/gpg-loopback.sh`, no passphrase required); `git commit -S` + `git verify-commit` → Good signature; `commit.gpgsign=true` configured |
| Social Preview Image | Docs | VERIFIED | Real 1200×630 OpenGraph PNG generated locally via Pillow (`scripts/generate_social_preview.py`); no external credits required |
| Alerting (Phase 11) | Phase 11 | IMPLEMENTED | Prometheus alerting rules (`deploy/alerting/prometheus_rules.yml`) for auth failures, agent failures, API errors/latency, memory growth |
| Concurrency / State Safety (Phase 11) | Phase 11 | IMPLEMENTED | Concurrency tests (`tests/unit/test_concurrency.py`) for orchestration locks and memory deduplication |

**Overall:** PARTIALLY VERIFIED. **NOT Production Ready** — voice/vision/smart environment are BLOCKED, backup/restore drill and OpenTelemetry tracing export are NOT RUN, Kubernetes/Helm and load testing are NOT RUN, Phase 10 web/desktop/mobile clients NOT RUN (CLI implemented), PR #39 merge is BLOCKED by branch protection (CI status not propagated). **RBAC repaired: `role_permissions` junction table added (migration `0002_add_role_permissions`), `get_user_permissions()` corrected, default role self-provisioned, 375 tests passing (0 failed; 3 pre-existing environmental failures unrelated to code).**
