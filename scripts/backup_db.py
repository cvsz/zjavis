"""JARVIS database backup tool.

Performs a compressed, custom-format ``pg_dump`` of the JARVIS PostgreSQL
database and optionally encrypts the backup at rest with ``age``.

Usage:
    python3 scripts/backup_db.py [--output /backups/jarvis-db.dump] [--encrypt]

Environment variables (or a .env file) provide connection settings:
    JARVIS_DATABASE_URL   PostgreSQL connection URL (required)
    JARVIS_BACKUP_DIR     Backup directory (default: ./backups)

Never commits real credentials; secrets come from the environment only.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from datetime import UTC, datetime
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
    """Extract connection params from a SQLAlchemy async URL for pg_dump."""
    # postgresql+psycopg://user:password@host:port/db
    from urllib.parse import urlparse

    parsed = urlparse(url)
    return {
        "host": parsed.hostname or "localhost",
        "port": str(parsed.port or 5432),
        "user": parsed.username or "postgres",
        "password": parsed.password or "",
        "dbname": parsed.path.lstrip("/") or "postgres",
    }


def backup(*, output: Path, encrypt: bool = False) -> Path:
    """Run pg_dump and return the path to the backup file."""
    params = _parse_db_url(_database_url())
    env = os.environ.copy()
    if params["password"]:
        env["PGPASSWORD"] = params["password"]
    elif os.getenv("PGPASSWORD"):
        env["PGPASSWORD"] = os.getenv("PGPASSWORD")

    output.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        "pg_dump",
        "-h",
        params["host"],
        "-p",
        params["port"],
        "-U",
        params["user"],
        "-d",
        params["dbname"],
        "-Fc",
        "-f",
        str(output),
    ]

    print(f"==> Backing up database {params['dbname']} to {output}")
    result = subprocess.run(cmd, check=False, env=env, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"pg_dump failed:\n{result.stderr}", file=sys.stderr)
        sys.exit(1)

    # Verify the backup is restorable (dry-run list)
    list_result = subprocess.run(
        ["pg_restore", "--list", str(output)],
        check=False,
        capture_output=True,
        text=True,
    )
    if list_result.returncode != 0:
        print(
            f"pg_restore --list verification failed:\n{list_result.stderr}",
            file=sys.stderr,
        )
        sys.exit(1)
    print(f"==> Backup verified: {output} ({output.stat().st_size} bytes)")

    backup_file = output
    if encrypt:
        encrypted = output.with_suffix(output.suffix + ".age")
        print(f"==> Encrypting backup at rest to {encrypted}")
        enc_cmd = [
            "age",
            "-r",
            os.getenv("BACKUP_RECIPIENT", "REPLACE_ME"),
            str(output),
        ]
        enc_result = subprocess.run(
            enc_cmd, check=False, capture_output=True, text=True
        )
        if enc_result.returncode != 0:
            print(f"age encryption failed:\n{enc_result.stderr}", file=sys.stderr)
            sys.exit(1)
        encrypted.write_bytes(enc_result.stdout)
        output.unlink()
        backup_file = encrypted
        print(f"==> Encrypted backup written: {backup_file}")

    return backup_file


def main() -> None:
    parser = argparse.ArgumentParser(description="Backup the JARVIS database")
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Backup output path (default: ./backups/jarvis-db-<timestamp>.dump)",
    )
    parser.add_argument(
        "--encrypt",
        action="store_true",
        help="Encrypt the backup at rest with age (requires BACKUP_RECIPIENT)",
    )
    args = parser.parse_args()

    if args.output is None:
        backup_dir = Path(os.getenv("JARVIS_BACKUP_DIR", "./backups"))
        timestamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
        args.output = backup_dir / f"jarvis-db-{timestamp}.dump"

    backup(output=args.output, encrypt=args.encrypt)


if __name__ == "__main__":
    main()
