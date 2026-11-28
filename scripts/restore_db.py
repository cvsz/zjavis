"""JARVIS database restore tool.

Restores a ``pg_dump`` custom-format backup into a fresh PostgreSQL
database, runs Alembic migrations, and validates row counts for all 14
core entities. Intended for isolated restore drills.

Usage:
    python3 scripts/restore_db.py --backup /backups/jarvis-db.dump [--decrypt]

Environment variables:
    JARVIS_DATABASE_URL   Target PostgreSQL connection URL (required)
    JARVIS_BACKUP_DIR     Backup directory (default: ./backups)

Never logs or exposes backup contents.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # pragma: no cover - python-dotenv optional at runtime
    pass


def _database_url() -> str:
    url = os.getenv("JARVIS_DATABASE_URL")
    if not url:
        print("ERROR: JARVIS_DATABASE_URL is not set", file=sys.stderr)
        sys.exit(2)
    return url


def _parse_db_url(url: str) -> dict[str, str]:
    from urllib.parse import urlparse

    parsed = urlparse(url)
    return {
        "host": parsed.hostname or "localhost",
        "port": str(parsed.port or 5432),
        "user": parsed.username or "postgres",
        "password": parsed.password or "",
        "dbname": parsed.path.lstrip("/") or "postgres",
    }


def _env() -> dict[str, str]:
    env = os.environ.copy()
    url = _database_url()
    params = _parse_db_url(url)
    if params["password"]:
        env["PGPASSWORD"] = params["password"]
    else:
        pgpass = os.getenv("PGPASSWORD")
        if pgpass is not None:
            env["PGPASSWORD"] = pgpass
    return env


def decrypt(*, encrypted: Path) -> Path:
    """Decrypt an age-encrypted backup, returning the decrypted path."""
    decrypted = encrypted.with_suffix("")  # strip .age
    if not decrypted.exists() or decrypted.suffix != ".dump":
        decrypted = encrypted.parent / (encrypted.stem.replace(".age", "") + ".dump")
    cmd = ["age", "-d", str(encrypted), "-o", str(decrypted)]
    print(f"==> Decrypting backup to {decrypted}")
    result = subprocess.run(cmd, check=False, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"age decryption failed:\n{result.stderr}", file=sys.stderr)
        sys.exit(1)
    return decrypted


def restore(*, backup: Path) -> None:
    """Restore a pg_dump backup into the target database."""
    params = _parse_db_url(_database_url())
    env = _env()

    print(f"==> Restoring database {params['dbname']} from {backup}")

    # Drop and recreate the target database is out of scope here; assume the
    # target database already exists and is empty/fresh. Use --clean to drop
    # existing objects before restoring.
    cmd = [
        "pg_restore",
        "-h",
        params["host"],
        "-p",
        params["port"],
        "-U",
        params["user"],
        "-d",
        params["dbname"],
        "--clean",
        "--if-exists",
        "--no-owner",
        str(backup),
    ]
    result = subprocess.run(cmd, check=False, env=env, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"pg_restore failed:\n{result.stderr}", file=sys.stderr)
        sys.exit(1)
    print("==> Restore complete")


def run_migrations() -> None:
    """Run Alembic migrations to bring the schema to head."""
    print("==> Running Alembic migrations to head")
    env = os.environ.copy()
    env["PYTHONPATH"] = "src"
    result = subprocess.run(
        ["alembic", "upgrade", "head"],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    if result.returncode != 0:
        print(f"Alembic upgrade failed:\n{result.stderr}", file=sys.stderr)
        sys.exit(1)
    print(result.stdout)
    print("==> Migrations complete")


CORE_TABLES = [
    "organizations",
    "users",
    "tenants",
    "roles",
    "permissions",
    "role_bindings",
    "role_permissions",
    "sessions",
    "conversations",
    "messages",
    "memories",
    "agents",
    "tasks",
    "approvals",
    "audit_events",
]


def validate_row_counts() -> None:
    """Verify all 14 core tables exist and are non-empty after restore."""
    import asyncio

    from sqlalchemy import text

    from jarvis.db.session import async_session

    async def _validate() -> None:
        async with async_session() as session:
            all_ok = True
            for table in CORE_TABLES:
                result = await session.execute(text(f'SELECT COUNT(*) FROM "{table}"'))
                count = result.scalar()
                status = "OK" if (count is not None and count > 0) else "EMPTY"
                if count is None or count == 0:
                    all_ok = False
                print(f"    {table}: {count} rows [{status}]")
            if not all_ok:
                print(
                    "ERROR: One or more core tables are empty after restore",
                    file=sys.stderr,
                )
                sys.exit(1)
            print("==> All 14 core tables present and non-empty")

    asyncio.run(_validate())


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Restore the JARVIS database from backup"
    )
    parser.add_argument(
        "--backup",
        type=Path,
        required=True,
        help="Path to the backup file (.dump or .dump.age)",
    )
    parser.add_argument(
        "--decrypt",
        action="store_true",
        help="Decrypt an age-encrypted backup before restoring",
    )
    args = parser.parse_args()

    backup_file = args.backup
    if args.decrypt:
        backup_file = decrypt(encrypted=args.backup)

    restore(backup=backup_file)
    run_migrations()
    validate_row_counts()
    print("==> Restore drill PASSED")


if __name__ == "__main__":
    main()
