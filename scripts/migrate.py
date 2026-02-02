"""
Database Migration CLI

Usage:
    python -m scripts.migrate status
    python -m scripts.migrate up
    python -m scripts.migrate down 2

Requires: PYTHONPATH=src (or run from repo root with src on path).
"""

import argparse
import asyncio
import os
import sys
from pathlib import Path

# Ensure src is on path for omen imports
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

# ruff: noqa: E402
from omen.infrastructure.database.migrations import (
    MigrationRunner,
    RISKCAST_MIGRATIONS,
)


async def main() -> None:
    parser = argparse.ArgumentParser(description="Database migrations")
    parser.add_argument("command", choices=["status", "up", "down"])
    parser.add_argument(
        "--target",
        type=int,
        help="Target version for rollback (required for 'down')",
    )
    parser.add_argument(
        "--db",
        default=os.environ.get("RISKCAST_DB_PATH", "/data/riskcast/signals.db"),
        help="Database path",
    )
    args = parser.parse_args()

    runner = MigrationRunner(args.db, RISKCAST_MIGRATIONS)

    if args.command == "status":
        current = await runner.get_current_version()
        pending = await runner.get_pending_migrations()
        print(f"Current version: {current}")
        print(f"Pending migrations: {len(pending)}")
        for m in pending:
            print(f"  - {m.version}: {m.description}")

    elif args.command == "up":
        applied = await runner.run()
        if applied:
            print(f"Applied migrations: {applied}")
        else:
            print("No pending migrations")

    elif args.command == "down":
        if args.target is None:
            print("Error: --target required for rollback (e.g. --target 2)")
            sys.exit(1)
        rolled_back = await runner.rollback(args.target)
        print(f"Rolled back migrations: {rolled_back}")


if __name__ == "__main__":
    asyncio.run(main())
