# Security Policy

Security is part of the default delivery baseline for repositories created from this template.

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


## zjavis Implemented Security Controls (verified)

The following controls are implemented in `cvsz/zjavis` and verified by testing and static analysis:

| Domain | Control | Implementation | Status |
|--------|---------|----------------|--------|
| Authentication | Password hashing | PBKDF2-HMAC-SHA256, 210,000 iterations (OWASP minimum), `src/jarvis/core/security.py` | VERIFIED |
| Authentication | Token signing | HMAC-SHA256 JWT, Python stdlib only (no third-party JWT dependency), `src/jarvis/core/security.py` | VERIFIED |
| Authentication | Token transmission | `Authorization: Bearer` header only; no query-string tokens, `src/jarvis/api/auth.py` | VERIFIED |
| Authorization | Permission model | Capability-based `Permission` class + `require_permission()`, `src/jarvis/core/security.py` | VERIFIED |
| Authorization | Policy engine | `PolicyEngine` with ALLOW/DENY/REQUIRE_APPROVAL/REQUIRE_REAUTHENTICATION/OUT_OF_SCOPE; default-deny, `src/jarvis/core/policy.py` | VERIFIED |
| Authorization | Execution-time policy enforcement | PolicyEngine middleware on all mutating API routes (POST/PUT/DELETE/PATCH), `src/jarvis/api/main.py` | VERIFIED |
| Authorization | Tenant isolation | All data-access endpoints scope by `tenant_id` (never `user.id`), `src/jarvis/api/*` | VERIFIED |
| Authorization | Approval gate | Medium/high-risk and `database.mutate`/`deployment.execute` require explicit approval, `src/jarvis/approval/` | VERIFIED |
| Input validation | SQL injection prevention | SQLAlchemy ORM with parameterized queries only | VERIFIED |
| Input validation | XSS / prompt injection | `sanitize_message_content()` blocks `<script>`, `javascript:`, `on*` handlers, `ignore previous instructions`, `system: you are`, `src/jarvis/api/conversations.py` | VERIFIED |
| Input validation | Idempotency key conflict | Duplicate idempotency key rejected with 409 Conflict, `src/jarvis/api/tasks.py` | VERIFIED |
| Secrets management | No hardcoded secrets | `.env` gitignored; `.env.example` placeholders only; `validate_repo.py` secret-content scan | VERIFIED |
| Secrets in logs | Secret redaction | `SecretFilter` redacts secret-like keys (password, token, secret, api_key, authorization, credential, private_key, session, cookie) from log records, `src/jarvis/core/logging.py` | VERIFIED |
| Production config | Fail-closed secret | `JARVIS_APP_SECRET` must be set when `JARVIS_APP_ENV=production`; default rejected, `src/jarvis/core/config.py` | VERIFIED |
| API security | CORS default-deny | `allow_credentials=False` with wildcard origins; explicit methods/headers only, `src/jarvis/api/main.py` | VERIFIED |
| API security | Rate limiting | 60 requests/minute per client IP; health/metrics exempt, `src/jarvis/api/main.py` | VERIFIED |
| API security | Security headers | `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer`, `Content-Security-Policy: default-src 'self'`, `src/jarvis/api/main.py` | VERIFIED |
| Audit | Tamper-evident events | `AuditEvent` records with tenant/actor/category/outcome; no secrets recorded, `src/jarvis/audit/` | VERIFIED |
| Cryptography | CSPRNG for jitter | `secrets.SystemRandom().uniform()` in orchestration backoff (Bandit B311 remediated), `src/jarvis/orchestration/executor.py` | VERIFIED |
| Streaming resilience | DB commit failure handling | SSE stream continues and reports done even if DB commit fails, `src/jarvis/api/conversations.py` | VERIFIED |

### Bandit Scan Results (latest)

| Severity | Count | Disposition |
|----------|-------|-------------|
| Undefined | 0 | — |
| Low | 2 | Both documented False Positives (`"bearer"` token type; fail-closed default-secret comparison) |
| Medium | 0 | — |
| High | 0 | — |

One B311 finding (non-crypto PRNG in orchestration jitter) was remediated and no longer appears.

No credentials, tokens, or private keys are committed to the repository. `.env` is untracked and gitignored.
