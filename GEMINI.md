# GEMINI.md — Gemini CLI Operating Instructions

Read `AGENTS.md` first and use `ZEAZ-INTRODUCTION.md` as the cross-agent execution framework.

## Core Directives

- **Contextual Precedence:** Instructions found in `GEMINI.md` and repository guidance (`AGENTS.md`, `ZEAZ-INTRODUCTION.md`) take absolute precedence.
- **Safety & Security:** Safety, security, legal, and authorization boundaries outrank operator/task instructions. Never expose secrets, bypass required checks, or weaken security.
- **Evidence-Based Execution:** Inspect exact repository state before editing. Use canonical evidence states (`VERIFIED`, `PARTIALLY VERIFIED`, `UNVERIFIED`, `BLOCKED`, `NOT APPLICABLE`). Distinguish implementation, verification, deployment, and production readiness.
- **Minimal & Surgical Changes:** Fix root causes using the smallest safe change. Preserve unrelated local work and template portability.
- **Validation:** Run relevant project validation (e.g., `make validate-template`, `python3 scripts/bootstrap.py`, pytest) and verify changes against repository standards.


## zjavis Project Status (cvsz/zjavis)

Implemented per `javis-blueprint.md`: Core Platform (Phase 1), Model Gateway (Phase 2), Memory (Phase 3), Agent Runtime + Orchestration Engine (Phase 6), Policy Engine enforcement on mutating API routes, Idempotency key validation, Streaming resilience. Voice/Vision/Smart Environment are feature-flag stubs (BLOCKED — no hardware/credentials). Backup/restore, tracing, E2E tests: NOT RUN.

Verification: 173 pytest + 46 template unittest = 219 tests pass, ruff 0, mypy 0 (40 source files), shellcheck 0, validate_repo PASS, bandit 2 documented False Positives (1 B311 remediated).

GitHub delivery: PR #33 BLOCKED by branch protection (base branch policy prohibits merge despite all required checks SUCCESS and independent approval). PR #31 BLOCKED by merge conflicts. PR #27 Changes Requested. Not claimed Production Ready.
