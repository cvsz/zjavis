# GEMINI.md — Gemini CLI Operating Instructions

Read `AGENTS.md` first and use `ZEAZ-INTRODUCTION.md` as the cross-agent execution framework.

## Core Directives

- **Contextual Precedence:** Instructions found in `GEMINI.md` and repository guidance (`AGENTS.md`, `ZEAZ-INTRODUCTION.md`) take absolute precedence.
- **Safety & Security:** Safety, security, legal, and authorization boundaries outrank operator/task instructions. Never expose secrets, bypass required checks, or weaken security.
- **Evidence-Based Execution:** Inspect exact repository state before editing. Use canonical evidence states (`VERIFIED`, `PARTIALLY VERIFIED`, `UNVERIFIED`, `BLOCKED`, `NOT APPLICABLE`). Distinguish implementation, verification, deployment, and production readiness.
- **Minimal & Surgical Changes:** Fix root causes using the smallest safe change. Preserve unrelated local work and template portability.
- **Validation:** Run relevant project validation (e.g., `python3 scripts/validate_repo.py`, `PYTHONPATH=src python3 -m pytest tests/`, `ruff check`, `mypy`) and verify changes against repository standards.

## zjavis applied context

- Repository: `cvsz/zjavis` (root: `/mnt/zdata/zjavis`)
- Blueprint: `javis-blueprint.md`
- Phase 1 (Core Platform): COMPLETE and VERIFIED — configuration, security, policy engine, logging, metrics, exceptions, 14 SQLAlchemy models, Alembic migration, auth, approval, audit, model gateway, memory service, agent runtime, orchestration engine, SSRF/path traversal prevention, and API routes.
- Phase 7 (Tool & Computer Integration): IMPLEMENTED — File, Terminal, Git, Docker, MCP, Browser adapters with SSRF/path traversal prevention, command allowlisting, output bounding, and tool registry.
- Phase 8 (Engineering Intelligence): IMPLEMENTED — Repository discovery, architecture analysis, engineering capability registry. All operations read-only and policy-governed.
- Security hardening: tenant-scoped policy enforcement on all mutating endpoints; tenant isolation on approval and conversation endpoints; `get_user_permissions()` scopes by tenant_id; `require_policy()` passes tenant context; SSRF/path traversal prevention; orchestration state transition validation.
- Do not claim production readiness without evidence for each readiness gate.
- Tests: 330 passing (225 unit/integration + 46 template + 59 Phase 7/8/RBAC; 0 failed). Verification baseline: Build PASS, Ruff PASS, MyPy PASS, ShellCheck PASS, Bandit 2 Low (documented False Positives), validate_repo PASS, Docker build PASS (`jarvis:local`).
- Authorization hardening (this session): `request_approval` endpoint now requires `require_policy()`; `execute_task` agent runtime endpoint now requires `require_policy()`; `state` field removed from `TaskUpdate` to prevent direct state mutation; login creates a `Session` record for token revocation support.
- Blocked/NOT RUN: Voice, Vision, Smart Environment (no hardware/credentials), Backup/Restore, OpenTelemetry tracing, K8s/Helm, load testing, E2E tests. GPG commit signing is VERIFIED functional via loopback pinentry (no TTY required).
- **Alembic migrations fixed:** `alembic/env.py` `connectable.dispose()` corrected for sync engine; `alembic upgrade head` verified passing against live PostgreSQL.
- RBAC repair (this session): Added `role_permissions` junction table (migration `0002_add_role_permissions`). Fixed `get_user_permissions()` join so roles carry atomic permissions. Default permissions, default "user" role, and caller role binding self-provisioned idempotently.
