## Summary

Apply authorization hardening to three API endpoints that were authentication-only, and finalize all project documentation.

## Changes

### Authorization hardening (security fixes)

1. **`POST /api/v1/approvals` (`request_approval`)** — Added `require_policy()` with `DEPLOYMENT_REQUEST` permission. Previously authenticated-only; any authenticated user could request approvals.
2. **`POST /api/v1/agent-runtime/execute` (`execute_task`)** — Added `require_policy()` with `REPOSITORY_WRITE` permission. Previously authenticated-only; any authenticated user could trigger agent task execution.
3. **`PUT /api/v1/tasks/{id}` (`update_task`)** — Removed `state` field from `TaskUpdate` model. Task state transitions are now enforced exclusively by the `OrchestrationEngine` state machine (`validate_state_transition()`), preventing direct state mutation via API.
4. **`POST /api/v1/auth/login`** — Login now persists a `Session` database record (token hash, expiry, tenant) for token tracking and revocation support.

### Documentation (all project docs synchronized)

- `README.md` — Full rewrite: Master Advanced Professional documentation with Bridge Status, all subsystems, security controls, configuration, API routes, architecture, getting started, project structure, evidence states, limitations.
- `AGENTS.md` — Updated required checks table (250 tests, 75 files, 40 source files); added security hardening section.
- `SECURITY.md` — Added authorization hardening findings table (A1-A4).
- `ROADMAP.md` — Added authorization hardening items to Phase 11.
- `OPENCODE.md`, `CLAUDE.md`, `GEMINI.md` — Updated test counts and security hardening notes.
- `ZEAZ-INTRODUCTION.md` — Updated evidence baseline; added authorization hardening section.
- `Final-Report.md` — Complete implementation report with findings, metrics, evidence-state summary.

## Verification

| Check | Result |
|-------|--------|
| Build (`py_compile`) | PASS |
| Ruff lint | PASS (0 errors, 0 warnings, 75 files) |
| Ruff format | PASS |
| MyPy | PASS (0 issues, 40 source files) |
| ShellCheck | PASS |
| Pytest (all) | PASS (250 passed, 0 failed) |
| Bandit | 2 Low (documented False Positives; 0 actual findings) |
| validate_repo | PASS |
| Docker build | PASS (`jarvis:local`) |

## Security Impact

- Authorization now enforced at execution time on `request_approval` and `execute_task` endpoints (default-deny).
- Task state mutation prevented via API — state transitions enforced by OrchestrationEngine only.
- Login session records enable token tracking and revocation.

## Documentation Impact

All 9 project documents updated and synchronized with source code changes.

## Deployment Impact

No new dependencies. No database migration changes (uses existing schema). Backward-compatible except `state` field removed from `TaskUpdate` request body.

## Rollback

Revert this commit; all changes are contained in 15 files. No data migration required.

## Test Coverage

- 2 new unit tests in `tests/unit/test_api_approvals.py` (ALLOW/DENY for `DEPLOYMENT_REQUEST`)
- Updated `tests/unit/test_api_tasks.py` (removed `state` field tests; added validation tests)

## Linked Issues

None.

---

Signed-off-by: cvsz <cvsz@core>
