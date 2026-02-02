"""
Reconcile State Store

Tracks reconcile progress and highwater marks.
Used to detect when re-reconcile is needed.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import aiosqlite

logger = logging.getLogger(__name__)


@dataclass
class ReconcileState:
    """State of last reconcile for a partition."""

    partition_date: str
    last_reconcile_at: datetime
    ledger_highwater: int
    manifest_revision: int
    ledger_record_count: int
    processed_count: int
    missing_count: int
    status: str  # "COMPLETED" | "PARTIAL" | "FAILED"


class ReconcileStateStore:
    """
    Persistent reconcile state tracking.

    Stores:
    - Last reconcile timestamp per partition
    - Highwater mark at time of reconcile
    - Record counts for audit

    Used to:
    - Detect if late arrivals occurred (highwater changed)
    - Avoid redundant reconciles
    - Track reconcile history
    """

    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialized = False

    async def _ensure_initialized(self) -> None:
        """Initialize schema."""
        if self._initialized:
            return

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("PRAGMA journal_mode=WAL")

            await db.execute("""
                CREATE TABLE IF NOT EXISTS reconcile_state (
                    partition_date TEXT PRIMARY KEY,
                    last_reconcile_at TEXT NOT NULL,
                    ledger_highwater INTEGER NOT NULL,
                    manifest_revision INTEGER NOT NULL,
                    ledger_record_count INTEGER NOT NULL,
                    processed_count INTEGER NOT NULL,
                    missing_count INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)

            await db.execute("""
                CREATE TABLE IF NOT EXISTS reconcile_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    partition_date TEXT NOT NULL,
                    reconcile_at TEXT NOT NULL,
                    ledger_highwater INTEGER NOT NULL,
                    ledger_record_count INTEGER NOT NULL,
                    processed_count INTEGER NOT NULL,
                    missing_count INTEGER NOT NULL,
                    replayed_count INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    duration_ms INTEGER,
                    error_message TEXT
                )
            """)

            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_history_partition
                ON reconcile_history(partition_date)
            """)

            await db.commit()

        self._initialized = True

    async def get_state(self, partition_date: str) -> Optional[ReconcileState]:
        """Get last reconcile state for partition."""
        await self._ensure_initialized()

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row

            async with db.execute(
                "SELECT * FROM reconcile_state WHERE partition_date = ?",
                (partition_date,),
            ) as cursor:
                row = await cursor.fetchone()

                if row:
                    return ReconcileState(
                        partition_date=row["partition_date"],
                        last_reconcile_at=datetime.fromisoformat(
                            row["last_reconcile_at"].replace("Z", "+00:00")
                        ),
                        ledger_highwater=row["ledger_highwater"],
                        manifest_revision=row["manifest_revision"],
                        ledger_record_count=row["ledger_record_count"],
                        processed_count=row["processed_count"],
                        missing_count=row["missing_count"],
                        status=row["status"],
                    )
                return None

    async def save_state(
        self,
        partition_date: str,
        ledger_highwater: int,
        manifest_revision: int,
        ledger_record_count: int,
        processed_count: int,
        missing_count: int,
        replayed_count: int,
        status: str,
        duration_ms: Optional[int] = None,
        error_message: Optional[str] = None,
    ) -> None:
        """Save reconcile state and history."""
        await self._ensure_initialized()

        now = datetime.now(timezone.utc).isoformat()

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO reconcile_state
                (partition_date, last_reconcile_at, ledger_highwater, manifest_revision,
                 ledger_record_count, processed_count, missing_count, status, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(partition_date) DO UPDATE SET
                    last_reconcile_at = excluded.last_reconcile_at,
                    ledger_highwater = excluded.ledger_highwater,
                    manifest_revision = excluded.manifest_revision,
                    ledger_record_count = excluded.ledger_record_count,
                    processed_count = excluded.processed_count,
                    missing_count = excluded.missing_count,
                    status = excluded.status,
                    updated_at = excluded.updated_at
            """,
                (
                    partition_date,
                    now,
                    ledger_highwater,
                    manifest_revision,
                    ledger_record_count,
                    processed_count,
                    missing_count,
                    status,
                    now,
                ),
            )

            await db.execute(
                """
                INSERT INTO reconcile_history
                (partition_date, reconcile_at, ledger_highwater, ledger_record_count,
                 processed_count, missing_count, replayed_count, status, duration_ms, error_message)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    partition_date,
                    now,
                    ledger_highwater,
                    ledger_record_count,
                    processed_count,
                    missing_count,
                    replayed_count,
                    status,
                    duration_ms,
                    error_message,
                ),
            )

            await db.commit()

    async def needs_reconcile(
        self,
        partition_date: str,
        current_highwater: int,
        current_revision: int,
    ) -> tuple[bool, str]:
        """
        Check if partition needs (re-)reconcile.

        Returns:
            (needs_reconcile, reason)
        """
        state = await self.get_state(partition_date)

        if state is None:
            return True, "never_reconciled"

        if state.status != "COMPLETED":
            return True, f"previous_status_{state.status.lower()}"

        if current_highwater > state.ledger_highwater:
            return True, (f"highwater_increased_{state.ledger_highwater}_to_{current_highwater}")

        # manifest_revision not used for needs_reconcile (Option A: highwater only)
        return False, "up_to_date"


_reconcile_store: Optional[ReconcileStateStore] = None


def get_reconcile_store() -> ReconcileStateStore:
    """Return singleton ReconcileStateStore (path from RISKCAST_DB_PATH env)."""
    global _reconcile_store
    if _reconcile_store is None:
        import os

        db_path = os.environ.get("RISKCAST_DB_PATH", "/var/lib/riskcast/signals.db")
        state_path = str(Path(db_path).parent / "reconcile_state.db")
        _reconcile_store = ReconcileStateStore(state_path)
    return _reconcile_store
