"""
Signal Store v2 — Async SQLite

True async database operations with aiosqlite.
"""

import json
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

import aiosqlite

logger = logging.getLogger(__name__)


@dataclass
class ProcessedSignal:
    """Processed signal record."""

    signal_id: str
    trace_id: str
    source_event_id: str
    ack_id: str
    processed_at: datetime
    emitted_at: datetime
    source: str
    signal_data: dict


class SignalStore:
    """
    Async signal storage with SQLite.

    Uses aiosqlite for non-blocking operations.
    WAL mode for concurrent read/write.
    """

    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialized = False

    async def _ensure_initialized(self) -> None:
        """Initialize database schema."""
        if self._initialized:
            return

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("PRAGMA journal_mode=WAL")
            await db.execute("PRAGMA busy_timeout=10000")  # 10s wait for concurrent writers

            await db.execute("""
                CREATE TABLE IF NOT EXISTS processed_signals (
                    signal_id TEXT PRIMARY KEY,
                    trace_id TEXT NOT NULL,
                    source_event_id TEXT NOT NULL,
                    ack_id TEXT NOT NULL UNIQUE,
                    processed_at TEXT NOT NULL,
                    emitted_at TEXT NOT NULL,
                    partition_date TEXT NOT NULL,
                    source TEXT NOT NULL,
                    signal_data TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)

            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_partition_date
                ON processed_signals(partition_date)
            """)

            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_trace_id
                ON processed_signals(trace_id)
            """)

            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_source
                ON processed_signals(source)
            """)

            await db.commit()

        self._initialized = True

    async def get_by_signal_id(self, signal_id: str) -> Optional[ProcessedSignal]:
        """Get processed signal by ID (for dedupe)."""
        await self._ensure_initialized()

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row

            async with db.execute(
                "SELECT * FROM processed_signals WHERE signal_id = ?",
                (signal_id,),
            ) as cursor:
                row = await cursor.fetchone()

                if row:
                    return ProcessedSignal(
                        signal_id=row["signal_id"],
                        trace_id=row["trace_id"],
                        source_event_id=row["source_event_id"],
                        ack_id=row["ack_id"],
                        processed_at=datetime.fromisoformat(row["processed_at"]),
                        emitted_at=datetime.fromisoformat(row["emitted_at"]),
                        source=row["source"],
                        signal_data=json.loads(row["signal_data"]),
                    )
                return None

    async def store(
        self,
        signal_id: str,
        trace_id: str,
        source_event_id: str,
        ack_id: Optional[str],
        processed_at: datetime,
        emitted_at: datetime,
        source: str,
        signal_data: dict,
    ) -> str:
        """
        Store processed signal.

        Returns:
            ack_id (generated if not provided)
        """
        await self._ensure_initialized()

        if not ack_id:
            ack_id = f"riskcast-ack-{uuid.uuid4().hex[:16]}"

        partition_date = emitted_at.date().isoformat()

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("PRAGMA busy_timeout=10000")
            await db.execute("""
                INSERT INTO processed_signals
                (signal_id, trace_id, source_event_id, ack_id,
                 processed_at, emitted_at, partition_date, source, signal_data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                signal_id,
                trace_id,
                source_event_id,
                ack_id,
                processed_at.isoformat(),
                emitted_at.isoformat(),
                partition_date,
                source,
                json.dumps(signal_data),
            ))
            await db.commit()

        return ack_id

    async def list_processed_ids(self, partition_date: str) -> list[str]:
        """List all signal_ids processed for a partition."""
        await self._ensure_initialized()

        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT signal_id FROM processed_signals WHERE partition_date = ?",
                (partition_date,),
            ) as cursor:
                rows = await cursor.fetchall()
                return [row[0] for row in rows]

    async def count_by_source(self, partition_date: str) -> dict[str, int]:
        """Count signals by source (hot_path vs reconcile)."""
        await self._ensure_initialized()

        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("""
                SELECT source, COUNT(*)
                FROM processed_signals
                WHERE partition_date = ?
                GROUP BY source
            """, (partition_date,)) as cursor:
                rows = await cursor.fetchall()
                return {row[0]: row[1] for row in rows}

    async def get_last_reconcile_highwater(
        self,
        partition_date: str,
    ) -> Optional[tuple[int, int]]:
        """
        Get last reconcile highwater for partition.

        Used to detect if re-reconcile needed.
        For MVP, return None (always reconcile).
        """
        return None


_store: Optional[SignalStore] = None


def get_store() -> SignalStore:
    """Return singleton SignalStore (path from RISKCAST_DB_PATH env)."""
    global _store
    if _store is None:
        import os
        path = os.environ.get("RISKCAST_DB_PATH", "/var/lib/riskcast/signals.db")
        _store = SignalStore(path)
    return _store
