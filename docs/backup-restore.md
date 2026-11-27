# Backup, Restore, and Disaster Recovery — JARVIS

This document describes the backup and restore procedures for the JARVIS
Personal AI Operating System. It is intended for operators and platform
engineers responsible for data durability and disaster recovery.

## Scope

This document covers:

- PostgreSQL database backups (authoritative transactional store)
- Redis cache backups (transient state; not the source of truth)
- Object storage / media backups (if configured)
- Configuration and secrets backups
- Restore drills and verification
- Disaster recovery runbooks

It does **not** cover voice audio, vision media, or IoT device state,
which are out of scope for this release.

## Recovery Objectives

| Objective | Target | Notes |
|-----------|--------|-------|
| RPO (Recovery Point Objective) | 24 hours | Daily automated backup |
| RTO (Recovery Time Objective) | 4 hours | Includes restore + validation |
| Backup retention | 30 days | Rotated automatically |
| Backup encryption | AES-256 | Encrypted at rest |
| Backup verification | Weekly | Restore drill in isolated environment |

These are **design targets**, not yet measured in production. No restore
drill has been performed for this release (see Final-Report.md).

## Backup Scope

### PostgreSQL (authoritative store)

All 14 core entities are stored in PostgreSQL:

- organizations, users, tenants, roles, permissions, role_bindings
- sessions, conversations, messages, memories
- agents, tasks, approvals, audit_events

Backup method: `pg_dump` custom format (`-Fc`) with compression, run
daily via cron or Kubernetes CronJob.

### Redis (transient cache)

Redis is used for transient state and rate-limit counters only. It is
**not** the source of truth for durable task state. Redis backups are
optional; data loss in Redis is acceptable.

### Object storage / media

If document ingestion or media uploads are enabled, back up the configured
S3-compatible bucket. Not implemented in this release.

### Configuration and secrets

Back up:

- `.env.example` (template only — never real `.env`)
- `docker-compose.yml` and environment variable definitions
- Alembic migration files (`alembic/versions/`)
- Dockerfile and deployment manifests

Never back up or store real credentials, tokens, or production secrets.

## Backup Procedure

### 1. Database backup (pg_dump)

```bash
# Export connection settings
# export PGPASSWORD="<db_password>"
# export PGHOST="<db_host>"
# export PGPORT="5432"
# export PGUSER="<db_user>"
# export PGDATABASE="<db_name>"

# Create timestamped backup
BACKUP_FILE="/backups/jarvis-db-$(date +%Y%m%d-%H%M%S).dump"
pg_dump -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" \
  -Fc -f "$BACKUP_FILE"

# Verify backup is restorable (dry-run)
pg_restore --list "$BACKUP_FILE" > /dev/null
```

### 2. Encrypt backup at rest

```bash
# Encrypt with age (preferred) or gpg
age -r "$BACKUP_RECIPIENT" "$BACKUP_FILE" > "$BACKUP_FILE.age"
shred -u "$BACKUP_FILE"
```

### 3. Copy off-site

Copy the encrypted backup to a separate failure domain (off-site object
storage, another region, or offline media).

### 4. Configuration backup

```bash
tar czf "/backups/jarvis-config-$(date +%Y%m%d).tar.gz" \
  docker-compose.yml Dockerfile alembic/ .env.example \
  src/jarvis/ requirements.txt requirements-dev.txt
```

## Restore Procedure

### 1. Provision a fresh PostgreSQL instance

```bash
# Start PostgreSQL 16
docker run --name jarvis-restore-postgres \
  -e POSTGRES_USER=jarvis -e POSTGRES_PASSWORD="<db_password>" \
  -e POSTGRES_DB=jarvis -p 5432:5432 \
  -d postgres:16-alpine
```

### 2. Decrypt and restore the database

```bash
# Decrypt (key handling omitted — secret material not shown)
age -d "<encrypted-backup>" -o "<decrypted-backup>"

# Restore
pg_restore -h localhost -p 5432 -U jarvis -d jarvis \
  --clean --if-exists --no-owner "$BACKUP_FILE"
```

### 3. Run migrations

```bash
export JARVIS_DATABASE_URL="postgresql+psycopg://jarvis:jarvis@localhost:5432/jarvis"
alembic upgrade head
```

### 4. Validate consistency

```bash
# Run the readiness probe
curl -f http://localhost:8000/ready

# Verify row counts per table
PYTHONPATH=src python3 -c "
from jarvis.db.session import async_session
from jarvis.db.models import *
import asyncio

async def main():
    async with async_session() as s:
        for m in [Organization, User, Tenant, Role, Permission,
                  RoleBinding, Session, Conversation, Message, Memory,
                  Agent, Task, Approval, AuditEvent]:
            r = await s.execute(select(m))
            print(f'{m.__tablename__}: {len(r.scalars().all())} rows')
asyncio.run(main())
"
```

### 5. Restore configuration

```bash
tar xzf "/backups/jarvis-config-$(date +%Y%m%d).tar.gz"
```

## Restore Drill

A restore drill must be performed on a schedule (recommended: quarterly)
and after any change to backup or restore procedures. The drill:

1. Restores the latest backup to an isolated environment.
2. Runs `alembic upgrade head`.
3. Starts the JARVIS API and hits `/ready`.
4. Verifies row counts for all 14 tables are non-zero.
5. Verifies a sample login and task creation flow.
6. Records the outcome (pass/fail, duration, RTO achieved).

**No restore drill has been performed for this release.** See
Final-Report.md §13 (Limitations and Items Not Verified).

## Disaster Recovery Runbooks

| Scenario | Detection | Containment | Recovery | Validation |
|----------|-----------|-------------|----------|------------|
| Database unavailable | `/ready` returns 503 | Fail closed; reject mutations | Restore from latest backup | `/ready` returns ready |
| Database corruption | Checksum failures | Stop writes; isolate instance | Point-in-time recovery | Row counts + spot checks |
| Backup failure | Backup job alert | Investigate storage/credentials | Retry backup; alert on-call | Backup completes successfully |
| Secret compromise | Audit alert / secret scan | Rotate affected credentials | Reissue tokens; revoke sessions | No unauthorized access |
| Complete site loss | Ingress timeout | Activate DR site | Restore from off-site backup | End-to-end user journey |

Runbooks are **documented but not yet implemented** as executable
scripts. See Final-Report.md for exact status.

## Backup Automation

No automated backup scripts are implemented in this release. Backups
must be performed manually using the procedures above until automation
is added (see Phase 11 / Production Hardening).

## Testing

Backup/restore tests are **NOT RUN** for this release. No backup code
exists in the codebase. See:

- Final-Report.md §13 (Limitations and Items Not Verified)
- ROADMAP.md Phase 11 (Production Hardening)

## Security

- Backups contain sensitive user data (conversations, messages, memories,
  audit events). Encrypt at rest and in transit.
- Store backup encryption keys separately from runtime credentials.
- Never log or expose backup contents.
- Restrict backup/restore access to authorized operators only.
- Audit all backup and restore operations.

## Related Documents

- `javis-blueprint.md` §18 (Backup, Recovery, and Data Lifecycle)
- `ROADMAP.md` Phase 11 (Production Hardening)
- `Final-Report.md` (implementation status and open findings)
