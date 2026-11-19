# Architecture

## Purpose

`ztemplate` is a language-agnostic repository foundation rather than an application runtime.

Its architecture is intentionally layered so generated projects can replace application-specific pieces without weakening repository governance.

## Layers

### Repository governance

Root policy documents define ownership, contribution, security, evidence, and release expectations:

- `AGENTS.md`
- `ZEAZ-INTRODUCTION.md`
- `GOVERNANCE.md`
- `SECURITY.md`
- `CONTRIBUTING.md`

### GitHub control plane

`.github/` provides CI/security/community baselines.

`scripts/github_admin.py` handles repository settings that cannot be enforced by committed files alone and verifies effective provider state after mutation.

### Validation

`scripts/validate_repo.py` checks required template structure and local Markdown links.

`tests/` validates bootstrap behavior.

Application-specific lint/test/build/security validation must be added by generated projects.

### Project initialization

`scripts/bootstrap.py` changes project identity/ownership routing only. It does not create application architecture or deploy infrastructure.

### AI/agent execution

`docs/ai/`, `skills/`, `components.d/`, and `plugins.d/` provide reusable agent execution guidance and discovery without making application-runtime assumptions.

### Application placeholders

The root Dockerfile and application Makefile targets are intentionally non-production placeholders. Generated projects replace them with stack-specific implementations.

## Existing-repository adoption

The architecture is composable. Established repositories should use [repository rollout](repository-rollout.md) and port only compatible missing layers rather than copying the tree wholesale.

## Production boundary

Repository-foundation readiness and application production readiness are separate claims.

The template can verify repository controls, documentation structure, and baseline automation. A generated application must independently verify runtime architecture, deployment, data, recovery, observability, capacity, security, and incident-response gates that apply to it.

## Shared Docker database and cache

Generated projects may use shared Docker database and cache services instead of application-managed embedded stores. This section describes the architecture pattern; generated projects replace placeholder service names and ports with their own stack-specific values.

### Architecture

```
Application
    -> DATABASE_URL = postgresql://<db_user>:<db_password>@<postgres_host>:<postgres_port>/<db_name>
    -> REDIS_URL    = redis://:<redis_password>@<redis_host>:<redis_port>/0
```

- **Database:** A shared PostgreSQL service reachable at `<postgres_host>:<postgres_port>`. The application connects using a dedicated database user (not the PostgreSQL superuser) with privileges limited to its own database.
- **Cache:** A shared Redis service reachable at `<redis_host>:<redis_port>`. Access is protected by a Redis password read from a runtime secret file, never embedded in the image or committed to version control.
- **Secret files:** Database and Redis passwords live in operator-managed runtime secret files (for example `/run/secrets/<project>_postgres_password` and `/run/secrets/<project>_redis_password`), mounted at deploy time. The application reads them at startup and never logs their contents.
- **User/database provisioning:** The deployment process (not the application runtime) creates the database user and database if they do not already exist. The application connects with least-privilege credentials.
- **Portability:** Placeholder service names (`<postgres_host>`, `<redis_host>`) and ports must be replaced by generated projects with their actual Docker service names, Compose service names, or external endpoints.

### Environment variables

| Variable | Placeholder example | Role |
|---|---|---|
| `DATABASE_URL` | `postgresql://<db_user>:<db_password>@<postgres_host>:<postgres_port>/<db_name>` | Application database connection string |
| `TEST_DATABASE_URL` | `postgresql://<db_user>:<db_password>@<postgres_host>:<postgres_port>/<db_name>` | Test-suite database connection string |
| `REPONAME_POSTGRES_HOST` | `<postgres_host>` | Shared database host |
| `REPONAME_POSTGRES_PORT` | `5432` | Shared database port |
| `REPONAME_POSTGRES_PASSWORD_FILE` | `/run/secrets/<project>_postgres_password` | Database password secret file |
| `REPONAME_REDIS_HOST` | `<redis_host>` | Shared cache host |
| `REPONAME_REDIS_PORT` | `6379` | Shared cache port |
| `REPONAME_REDIS_PASSWORD_FILE` | `/run/secrets/<project>_redis_password` | Redis password secret file |

### Security expectations

- Never commit real passwords, tokens, or connection strings containing credentials.
- Secret files must have mode `0600` and be mounted from operator-controlled secret storage.
- The application must fail closed if a required secret file is missing or unreadable.
- Queue and application payloads must not contain credential-like fields (password, token, secret, cookie, authorization, browser state).
- Database and Redis connection details are configuration, not evidence of production readiness; a generated project must independently verify runtime connectivity and authentication.
