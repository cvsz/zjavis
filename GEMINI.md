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
- Phase 1 (Core Platform): COMPLETE and VERIFIED
- Do not claim production readiness without evidence for each readiness gate
