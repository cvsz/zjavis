# AGENTS.md — zjavis Repository Agent Contract

## Purpose

This repository is the `cvsz/zjavis` project — JARVIS, a Personal AI Operating System.
It is a modular, security-first AI platform built on the javis-blueprint.md specification.
Changes must remain generic where applicable, secure by default, easy to customize, and safe to inherit.

## Project identity

- **Repository:** `cvsz/zjavis` (root: `/mnt/zdata/zjavis`)
- **Blueprint:** `javis-blueprint.md`
- **Architecture:** Modular monolith control plane (Python 3.14 / FastAPI / SQLAlchemy async / PostgreSQL)
- **Phase status:** Phase 1 (Core Platform) COMPLETE and VERIFIED; Phase 7 (Tool & Computer Integration) IMPLEMENTED; Phase 8 (Engineering Intelligence) IMPLEMENTED; Phases 2-6, 9-11 partially implemented or BLOCKED/NOT RUN (see Final-Report.md)
- **Version:** 0.1.0

## Operating rules

- Read README.md, CONTRIBUTING.md, SECURITY.md, ROADMAP.md, javis-blueprint.md, and the closest AGENTS.md before editing.
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

### Required checks for zjavis

| Check | Command | Result |
|-------|---------|--------|
| Build | `python3 -m py_compile src/jarvis/**/*.py tests/unit/*.py scripts/*.py` | PASS |
| Ruff lint | `python3 -m ruff check src/ tests/ scripts/` | PASS (0 errors, 0 warnings, 106 files) |
| Ruff format | `python3 -m ruff format --check src/ tests/ scripts/` | PASS (106 files already formatted) |
| MyPy | `python3 -m mypy --explicit-package-bases src/jarvis` | PASS (0 issues in 53 source files) |
| ShellCheck | `shellcheck -s bash scripts/*.sh .github/scripts/*.sh` | PASS (no errors) |
| Pytest (unit + integration) | `PYTHONPATH=src python3 -m pytest tests/unit tests/integration` | 372 passed, 0 failed |
| Pytest (template) | `PYTHONPATH=src python3 -m pytest tests/test_*.py` | 46 passed, 48 subtests passed |
| Pytest (all) | `PYTHONPATH=src python3 -m pytest tests/` | 372 passed, 0 failed |
| Bandit (security) | `bandit -r src/jarvis` | 2 Low (both documented False Positives; 0 actual findings) |
| validate_repo | `python3 scripts/validate_repo.py` | PASS |
| Docker build | `docker build -t jarvis:local .` | PASS (image `jarvis:local` built successfully) |
| Runtime validation | `docker run jarvis:local` then `GET /health` | PASS (HTTP 200); `/ready` returns 503 fail-closed when DB unavailable |

### Security hardening applied (this session)

- `request_approval` endpoint now requires `require_policy()` with `DEPLOYMENT_REQUEST` permission (was authentication-only).
- `execute_task` agent runtime endpoint now requires `require_policy()` with `REPOSITORY_WRITE` permission (was authentication-only).
- `state` field removed from `TaskUpdate` model — task state transitions are enforced exclusively by the OrchestrationEngine state machine, preventing direct state mutation via API.
- Login endpoint now creates a `Session` database record for token tracking and revocation support.
- `AgentRuntime.execute_task()` now enforces tenant isolation (tenant_id/user_id scope checked against the target task) before execution.
- Engineering capabilities (repository discovery, architecture analysis) now self-register in the engineering capability registry on package import.
- Terminal adapter default changed to `enabled=False` (security-by-default; all adapters disabled unless explicitly enabled).
- `alembic/env.py` fixed: `connectable.dispose()` no longer awaited on sync engine (was `await connectable.dispose()` raising `TypeError: 'NoneType' object can't be awaited`, blocking all Alembic migrations); `alembic upgrade head` verified passing against live PostgreSQL.

## Pull requests and releases

PRs must state scope, tests, security impact, compatibility/migration impact, documentation impact, deployment impact, and rollback. Releases require green required checks and explicit evidence; never infer production readiness from documentation alone.

## Security

Report vulnerabilities through SECURITY.md, not public issues. Security-related templates must redirect sensitive reports accordingly. Fail closed when a security-sensitive configuration is incomplete.

### zjavis security controls

- **Authentication:** PBKDF2-HMAC-SHA256 (210,000 iterations), HMAC-SHA256 JWT tokens (stdlib only), header-based Bearer transmission
- **Authorization:** PolicyEngine with default-deny, execution-time decisions (ALLOW/DENY/REQUIRE_APPROVAL/REQUIRE_REAUTHENTICATION/OUT_OF_SCOPE), capability-based permissions
- **Input validation:** SQLAlchemy ORM parameterized queries; `sanitize_message_content()` blocks XSS and prompt injection patterns
- **CORS:** Default-deny; `allow_credentials=False` with wildcard origins
- **Security headers:** `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer`, `Content-Security-Policy: default-src 'self'`
- **Rate limiting:** 60 requests per minute per client IP (in-memory store)
- **Secret redaction:** `SecretFilter` redacts secret-like values from logs
- **Secrets management:** No hardcoded secrets; `.env` is gitignored; `.env.example` contains placeholders only
- **Tenant isolation:** All data-access endpoints scope resources by tenant ID
- **Production fail-closed:** `JARVIS_APP_SECRET` must be set when `JARVIS_APP_ENV=production`
- **Policy enforcement:** `require_policy()` dependency applied to mutating API endpoints (tasks, agents, approvals, memory, conversations)

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
