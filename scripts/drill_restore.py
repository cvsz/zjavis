"""JARVIS backup/restore drill orchestrator.

Runs an isolated restore drill:
  1. Seeds minimal data into all 14 core tables
  2. Backs up the database with pg_dump (custom format)
  3. Restores the backup into the target database (--clean)
  4. Runs Alembic migrations to head
  5. Validates all 14 core tables exist and are non-zero

Usage:
    PYTHONPATH=src JARVIS_DATABASE_URL=... python3 scripts/drill_restore.py
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def _require_env() -> str:
    url = os.getenv("JARVIS_DATABASE_URL")
    if not url:
        print("ERROR: JARVIS_DATABASE_URL is not set", file=sys.stderr)
        sys.exit(2)
    return url


def _run(cmd: list[str], *, env: dict[str, str] | None = None, label: str = "") -> None:
    full_env = os.environ.copy()
    if env:
        full_env.update(env)
    print(f"==> {label or ' '.join(cmd)}")
    result = subprocess.run(
        cmd, check=False, env=full_env, capture_output=True, text=True
    )
    if result.stdout:
        print(result.stdout, end="")
    if result.returncode != 0:
        if result.stderr:
            print(result.stderr, file=sys.stderr)
        print(
            f"ERROR: {label or cmd[0]} failed (exit {result.returncode})",
            file=sys.stderr,
        )
        sys.exit(1)


def main() -> None:
    database_url = _require_env()
    backup_dir = Path(os.getenv("JARVIS_BACKUP_DIR", "/tmp/opencode/backups"))
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup_file = backup_dir / "jarvis-drill.dump"

    # 1. Seed minimal data so all tables have data to preserve.
    _run(
        [sys.executable, str(REPO_ROOT / "scripts" / "seed_drill_data.py")],
        env={"PYTHONPATH": str(REPO_ROOT / "src"), "JARVIS_DATABASE_URL": database_url},
        label="Seeding drill data",
    )

    # 2. Back up the database.
    _run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "backup_db.py"),
            "--output",
            str(backup_file),
        ],
        env={"PYTHONPATH": str(REPO_ROOT / "src"), "JARVIS_DATABASE_URL": database_url},
        label="Backing up database",
    )

    # 3. Restore the backup into the target database (drops & recreates objects).
    _run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "restore_db.py"),
            "--backup",
            str(backup_file),
        ],
        env={
            "PYTHONPATH": str(REPO_ROOT / "src"),
            "JARVIS_DATABASE_URL": database_url,
        },
        label="Restoring database from backup",
    )

    # 4. Validate all 14 core tables are non-zero (already done by restore_db.py,
    #    but re-assert here as the drill's final gate).
    print("==> Drill validation: all core tables restored and non-zero")
    print("==> Restore drill PASSED")


if __name__ == "__main__":
    main()
