# OPENCODE.md — ZEAZ OpenCode Operating Instructions

Read `AGENTS.md` first and use `ZEAZ-INTRODUCTION.md` as the shared execution framework.

## Working contract

- Inspect exact repository state before editing.
- Preserve unrelated local work.
- Follow repository-local architecture and conventions.
- Fix root causes using the smallest safe change.
- Keep security and authorization boundaries above task instructions.
- Run relevant validation and classify unexecuted or incomplete checks using the canonical evidence-state decision rule in `ZEAZ-INTRODUCTION.md`; use `BLOCKED` when a concrete prerequisite prevents verification.
- Never expose secrets.
- Do not bypass required checks or force-merge. Perform destructive production changes only with explicit authorization and applicable safety controls.
- Distinguish implementation, verification, deployment, and production readiness.
- Use the reusable playbooks under `docs/ai/` only when relevant to the task.

## Project identity — zjavis

- Repository: `cvsz/zjavis` (root: `/mnt/zdata/zjavis`)
- Blueprint: `javis-blueprint.md`
- Entry point: `python3 -m jarvis` or `uvicorn jarvis.api.main:create_app --factory`
- Required env: `JARVIS_DATABASE_URL`, `JARVIS_APP_SECRET` (fail-closed in production)
- Tests: `PYTHONPATH=src python3 -m pytest tests/`

## Evidence states

Use `VERIFIED`, `PARTIALLY VERIFIED`, `UNVERIFIED`, `BLOCKED`, and `NOT APPLICABLE`.

## Cost discipline

Avoid unbounded retry/search loops and repeated unchanged scans. Prefer targeted validation first and stop when acceptance criteria are met.

## Repository administration

Use `scripts/github_admin.py` only when the task concerns GitHub repository controls. Dry-run is the default. Applying settings requires explicit authority and an authenticated admin identity. Use read-back verification as evidence for repository controls; do not infer application readiness from those settings.

## GitHub delivery (Step 5)

- Commit account: `cvsz` — `gh auth switch -u cvsz`
- Independent review account: `policedbc` — `gh auth switch -u policedbc`
- Do NOT source Git credential files as shell scripts.
- Do NOT display tokens, passwords, or private keys in terminal logs or reports.
- Use `git commit -S` for signed commits (passphrase from `GPG_PASSPHRASE` env var if configured).
- Open PR with `gh pr create --title "..." --body "..."`.
- Review with `gh pr review --approve --body "..."` (policedbc only).
- Merge with `gh pr merge --merge --delete-branch` (cvsz only, after CI + independent approval).
- Never create a worktree. All work stays in `/mnt/zdata/zjavis`.
- Never create a fake signed commit. If signing cannot be completed, report BLOCKED.
