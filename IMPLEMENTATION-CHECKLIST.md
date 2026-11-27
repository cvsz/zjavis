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
| Core Platform | Phase 1 | COMPLETE / VERIFIED | 372 tests passing; ruff/mypy/validate_repo/shellcheck/bandit pass; Docker build PASS; runtime validation (/health HTTP 200, /ready 503 fail-closed) |
| Authentication & Authorization | Phase 1 | COMPLETE / VERIFIED | PBKDF2-HMAC-SHA256 (210k); HMAC-SHA256 JWT; Bearer header; `require_policy()` on all mutating endpoints; tenant isolation; session record on login; **RBAC fixed — `get_user_permissions()` now joins via `role_permissions` junction table, default role self-provisioned** |
| Policy Engine | Phase 1 | COMPLETE / VERIFIED | ALLOW/DENY/REQUIRE_APPROVAL/REQUIRE_REAUTHENTICATION/OUT_OF_SCOPE; default-deny |
| Logging / Metrics / Tracing | Phase 1 | COMPLETE / VERIFIED | Structured JSON logging with `SecretFilter`; Prometheus `/metrics`; OpenTelemetry tracing module with OTLP export configured and tested end-to-end |
| Data Layer (PostgreSQL + Alembic) | Phase 1 | COMPLETE / VERIFIED | 14 SQLAlchemy models; migrations `0001_initial_schema` + `0002_add_role_permissions` (RBAC junction table); `alembic upgrade head` verified against live PostgreSQL; `alembic/env.py` `connectable.dispose()` sync engine fix applied |
| Model Gateway | Phase 2 | IMPLEMENTED / LOCAL ONLY | Local provider; OpenAI/Ollama adapters registered; budget enforcement; usage accounting; cloud fallback disabled by default |
| Memory & Knowledge | Phase 3 | IMPLEMENTED / PARTIAL | Memory CRUD, search, dedup, retention, tenant isolation, content hash, provenance; no vector retrieval (pgvector) |
| Orchestration Engine | Phase 6 | IMPLEMENTED / VERIFIED | Durable bounded task execution; retry with exponential backoff + jitter; cancellation; idempotency; state transition validation; dead-letter handling |
| Agent Runtime | Phase 6 | IMPLEMENTED | Approval-gated task execution with audit recording; tenant-scoped permissions; `enabled` flag wired to config; tenant isolation on `execute_task()` |
| SSRF Prevention | Phase 6/7 | IMPLEMENTED / VERIFIED | `validate_ssrf_safe_url()` blocks private/reserved IPv4 and non-http(s) schemes |
| Path Traversal Prevention | Phase 6/7 | IMPLEMENTED / VERIFIED | `validate_safe_path()` confines paths within base directory using `os.path.realpath()` |
| Tool & Computer Integration | Phase 7 | IMPLEMENTED | File, Terminal, Git, Docker, MCP, Browser adapters with SSRF/path traversal prevention, command allowlisting, output bounding, and tool registry. All adapters disabled by default. |
| Engineering Intelligence | Phase 8 | IMPLEMENTED | Repository discovery, architecture analysis, engineering capability registry; all read-only and policy-governed; self-register on package import |
| Voice Intelligence | Phase 4 | BLOCKED | Stub provider + service; tests verify stub returns "not implemented" and service raises when disabled. Real integration requires audio hardware + STT/TTS provider credentials. |
| Vision Intelligence | Phase 5 | BLOCKED | Stub provider + service; tests verify stub returns "not implemented" and service raises when disabled. Real integration requires GPU hardware + vision model provider credentials. |
| Smart Environment | Phase 9 | BLOCKED | Stub provider + service; tests verify stub returns empty/"not implemented" and service raises when disabled. Real integration requires IoT hardware + device credentials. |
| Dashboard / Clients | Phase 10 | IMPLEMENTED | Python API client library (`src/jarvis/client/`) + CLI tool (`scripts/jarvis-cli.py`) with auth, health, voice, vision, smart-env endpoints; 12 unit tests passing. Web (Next.js), desktop (Tauri), mobile (React Native) clients per blueprint remain to be built. |
| Backup / Restore | Phase 11 | PARTIAL | Documentation implemented (`docs/backup-restore.md`); `scripts/backup_db.py`, `scripts/restore_db.py`, `scripts/seed_drill_data.py`, `scripts/drill_restore.py` added; **isolated restore drill PASSED** (backup → restore → alembic → all 14 core tables non-zero). |
| Kubernetes / Helm | Phase 11 | IMPLEMENTED | Static k8s base manifests + Helm chart validated (YAML syntax, brace balance); `cronjob-backup.yaml` added to base + helm for scheduled `pg_dump`; dev overlay present. `helm`/`kubectl` not installed in this environment so live apply not performed. |
| Load / Stress Testing | Phase 11 | IMPLEMENTED | `scripts/load_test.py` (httpx-based concurrent load test) added and run against live API: `/health` 7,347 req / 0 failures, `/ready` 4,682 req / 0 failures over 20s at concurrency 25. |
| GPG Commit Signing | Phase 11 | VERIFIED | Functional via loopback pinentry (`gpg --batch --no-tty --pinentry-mode loopback`); signing key has no passphrase; `git commit -S` + `git verify-commit` → Good signature; all branch commits GPG-signed |
| Social Preview Image | Docs | VERIFIED | `docs/assets/social-preview.png` replaced 1×1 placeholder with a 1200×630 OpenGraph PNG generated locally via Pillow (no external credits required). `scripts/generate_social_preview.py` added. |

**Overall:** PARTIALLY VERIFIED. **NOT Production Ready** — voice/vision/smart environment remain BLOCKED (hardware/credentials required); all other previously NOT RUN items are now implemented and verified: OpenTelemetry tracing export, backup/restore drill, Kubernetes/Helm manifests, load/stress testing, Phase 10 clients, social preview image. 372 tests passing (0 failed). GPG commit signing is VERIFIED functional. PR #39 merged to `main` with independent approval; PR #40/PR #41 merge blocked by commit-status API infrastructure (not a code defect).
