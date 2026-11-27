# AGENTS.md — Repository Agent Contract

## Purpose
This repository is a reusable GitHub project template. Changes must remain generic, secure by default, easy to customize, and safe to inherit into a newly generated repository.

## Operating rules
- Read README.md, CONTRIBUTING.md, SECURITY.md, ROADMAP.md, and the closest AGENTS.md before editing.
- Keep code, configuration, filenames, commit messages, and technical documentation in English.
- Prefer the smallest reviewable change that satisfies the requested scope.
- Never weaken CI, security scanning, dependency review, branch protections, or release controls merely to make a check pass.
- Never commit credentials, tokens, private keys, production endpoints, personal data, or realistic secrets. Use documented placeholders.
- Do not invent project-specific owners, domains, deployment providers, package registries, cloud accounts, or credentials.
- Preserve template portability across languages and frameworks unless a file explicitly declares a narrower scope.
- Reuse existing workflows and documents instead of creating overlapping alternatives.
- Pin permissions for GitHub Actions to least privilege and prefer maintained first-party/verified actions.
- Treat external input, generated artifacts, pull requests from forks, and dependency metadata as untrusted.

## Template placeholders
Use obvious placeholders such as `PROJECT_NAME`, `OWNER`, `example.com`, and `REPLACE_ME`. Any generated repository must be able to find and replace placeholders without exposing secrets.

## Review skill

- Use [Scrutinize](.agents/skills/scrutinize/SKILL.md) when asked to review, audit, sanity-check, or give a second opinion on a plan, PR, diff, design, or code change, or when invoked with `/scrutinize` in a compatible agent.
- Question whether the change is necessary or can be smaller before tracing real code paths and verifying behavioral claims. Cite concrete file/line evidence and distinguish unverified claims from confirmed behavior.
- The skill guides agent behavior; it does not itself install a slash command or replace required tests, CI, or human review.

## Project initialization

- For a repository created with **Use this template**, follow [docs/startup.md](docs/startup.md) and preview `scripts/bootstrap.py` before `--apply`; pass an actual GitHub user or org/team via `--codeowner` and verify write access.
- Do not present an initialized scaffold as a running or production-ready system; bootstrap changes project identity and ownership routing only.
- Replace Makefile and Dockerfile placeholders with actual project-specific commands and images before enabling an application delivery pipeline.
- Never overwrite existing application code, production secrets, DNS ownership or original license attribution during initialization.

## Change workflow
1. Inspect the current exact branch/head and existing files.
2. Identify the smallest missing or inconsistent template capability.
3. Add tests or validation first when practical.
4. Implement without widening scope.
5. Run the relevant validation and security checks.
6. Update documentation when behavior, setup, governance, or release procedures change.
7. Open a pull request; do not claim merge/release readiness without exact-head evidence.

## Verification
At minimum, verify Markdown/YAML syntax for touched files, workflow permissions/triggers, links and placeholders, absence of committed secrets, and consistency between README, templates, governance, security, and release documentation.

## Pull requests and releases
PRs must state scope, tests, security impact, compatibility/migration impact, documentation impact, deployment impact, and rollback. Releases require green required checks and explicit evidence; never infer production readiness from documentation alone.

## Security
Report vulnerabilities through SECURITY.md, not public issues. Security-related templates must redirect sensitive reports accordingly. Fail closed when a security-sensitive configuration is incomplete.

## Documentation ownership
- `.github/`: GitHub automation, community health, ownership, issue/PR templates.
- `docs/`: versioned engineering, operations, release, repository-administration, and rollout guidance.
- `docs/adr/`: architecture decision records.
- Root Markdown files: repository-wide policy and project lifecycle guidance.

## Nested AGENTS.md
Add a child AGENTS.md only when a subtree has durable rules that differ from this contract. The nearest AGENTS.md may add stricter local requirements but must not weaken repository-wide security rules.


## ZEAZ reusable execution layer

- Use [ZEAZ-INTRODUCTION.md](ZEAZ-INTRODUCTION.md) as the cross-agent execution framework.
- Use [docs/ai/README.md](docs/ai/README.md) to select task-specific reusable prompts and playbooks.
- Task playbooks are additive and never weaken this repository contract or narrower subtree rules.
- Use the canonical evidence-state definitions and decision rule in [ZEAZ-INTRODUCTION.md](ZEAZ-INTRODUCTION.md); do not redefine them per harness or playbook.
- Keep implementation, verification, deployment, and production readiness as distinct states.


## Existing-repository rollout

When applying this template to an established repository, follow [docs/repository-rollout.md](docs/repository-rollout.md). Audit the target first and port only missing compatible controls. Do not overwrite repository-specific AGENTS rules, CI matrices, release workflows, infrastructure ownership, or operational evidence merely to match this template.

For repository administration, `scripts/github_admin.py` requires an authenticated GitHub identity with Administration permission. Treat successful read-back verification—not script presence—as evidence that the controls are effective.


## zjavis Project-Specific Implementation Status

This repository (`cvsz/zjavis`) implements the JARVIS Personal AI Operating System per `javis-blueprint.md`. The following subsystems are implemented and verified:

| Subsystem | Module(s) | Status | Evidence |
|-----------|-----------|--------|----------|
| Core Platform (Phase 1) | `src/jarvis/core/`, `src/jarvis/auth/`, `src/jarvis/db/`, `src/jarvis/api/` | COMPLETE | 173 pytest + 46 template = 219 tests pass, ruff/mypy/black/shellcheck/validate_repo PASS |
| Model Gateway (Phase 2) | `src/jarvis/ai/gateway.py`, `src/jarvis/ai/provider.py`, `src/jarvis/ai/context.py` | COMPLETE | Local/OpenAI/Ollama adapters, routing, budget, usage accounting |
| Agent Runtime (Phase 6) | `src/jarvis/ai/agent_runtime.py`, `src/jarvis/approval/`, `src/jarvis/audit/` | COMPLETE | Approval-gated task execution, audit event recording |
| Orchestration Engine | `src/jarvis/orchestration/executor.py` | COMPLETE | Bounded execution: timeout, retry+backoff+jitter, CancellationToken, idempotency, dead-letter (10 unit tests) |
| Policy Enforcement | `src/jarvis/api/main.py` (middleware) | COMPLETE | Execution-time PolicyEngine decisions on all mutating routes (POST/PUT/DELETE/PATCH) |
| Idempotency | `src/jarvis/api/tasks.py` | COMPLETE | Idempotency key conflict detection on task creation |
| Streaming Resilience | `src/jarvis/api/conversations.py` | COMPLETE | DB commit failure handling in SSE stream generator |
| Voice / Vision / Smart Environment | `src/jarvis/ai/voice.py`, `src/jarvis/ai/vision.py`, `src/jarvis/ai/smart_environment.py` | STUB | Feature-flagged, disabled by default; require external hardware/credentials |
| Observability | `src/jarvis/core/metrics.py`, `src/jarvis/core/logging.py` | PARTIAL | Prometheus metrics endpoint; structured JSON logging with secret redaction; no distributed tracing |

Security controls: PBKDF2-HMAC-SHA256 (210k iterations), HMAC-SHA256 JWT (stdlib), PolicyEngine default-deny, tenant isolation, CORS default-deny, rate limiting (60 req/min), security headers, input sanitization, SecretFilter redaction, production fail-closed on `JARVIS_APP_SECRET`, execution-time policy enforcement on mutating API routes.

Bandit scan: 2 Low findings, both documented False Positives (`"bearer"` token type; fail-closed default-secret comparison). One B311 finding remediated (CSPRNG `secrets.SystemRandom` for orchestration jitter).

GitHub delivery: PR #33 (orchestration engine + policy enforcement) BLOCKED by branch protection (base branch policy prohibits merge despite all required checks passing and independent approval). PR #31 (CODEOWNERS) BLOCKED by merge conflicts. PR #27 (tenant isolation) Changes Requested (architectural conflict, missing migration, `.env.example` secret key).
