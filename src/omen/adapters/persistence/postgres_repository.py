"""
PostgreSQL-backed Signal Repository.

Enables horizontal scaling and persistent storage.
Production-ready implementation with connection pooling.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Optional

from ...application.ports.signal_repository import SignalRepository, AsyncSignalRepository
from ...domain.models.omen_signal import OmenSignal

logger = logging.getLogger(__name__)


class PostgresSignalRepository(SignalRepository):
    """
    Production-ready PostgreSQL repository.

    Supports:
    - Connection pooling via asyncpg
    - Async operations
    - Horizontal scaling (multiple instances)
    - UPSERT for idempotency

    Requires:
    - asyncpg library: pip install asyncpg
    - PostgreSQL 12+
    """

    def __init__(
        self,
        dsn: str,
        min_pool_size: int = 5,
        max_pool_size: int = 20,
    ):
        """
        Initialize PostgreSQL repository.

        Args:
            dsn: PostgreSQL connection string (e.g., "postgresql://user:pass@host:5432/db")
            min_pool_size: Minimum connections in pool
            max_pool_size: Maximum connections in pool
        """
        self.dsn = dsn
        self.min_pool_size = min_pool_size
        self.max_pool_size = max_pool_size
        self._pool = None
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize connection pool and create tables."""
        try:
            import asyncpg
        except ImportError:
            raise ImportError(
                "asyncpg is required for PostgreSQL support. " "Install with: pip install asyncpg"
            )

        self._pool = await asyncpg.create_pool(
            self.dsn,
            min_size=self.min_pool_size,
            max_size=self.max_pool_size,
        )
        await self._create_tables()
        self._initialized = True
        logger.info(
            "PostgreSQL repository initialized with pool size %d-%d",
            self.min_pool_size,
            self.max_pool_size,
        )

    async def _create_tables(self) -> None:
        """Create tables if they don't exist."""
        async with self._pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS omen_signals (
                    id SERIAL PRIMARY KEY,
                    signal_id VARCHAR(64) UNIQUE NOT NULL,
                    source_event_id VARCHAR(128),
                    trace_id VARCHAR(64),
                    input_event_hash VARCHAR(64),
                    title TEXT NOT NULL,
                    description TEXT,
                    probability FLOAT,
                    confidence_score FLOAT,
                    confidence_level VARCHAR(16),
                    signal_type VARCHAR(32),
                    status VARCHAR(16),
                    category VARCHAR(32),
                    tags JSONB DEFAULT '[]',
                    geographic JSONB,
                    temporal JSONB,
                    evidence JSONB DEFAULT '[]',
                    payload JSONB NOT NULL,
                    generated_at TIMESTAMPTZ NOT NULL,
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    updated_at TIMESTAMPTZ DEFAULT NOW()
                );
                
                -- Indexes for common queries
                CREATE INDEX IF NOT EXISTS idx_omen_signals_signal_id 
                    ON omen_signals(signal_id);
                CREATE INDEX IF NOT EXISTS idx_omen_signals_hash 
                    ON omen_signals(input_event_hash);
                CREATE INDEX IF NOT EXISTS idx_omen_signals_event_id 
                    ON omen_signals(source_event_id);
                CREATE INDEX IF NOT EXISTS idx_omen_signals_generated_at 
                    ON omen_signals(generated_at DESC);
                CREATE INDEX IF NOT EXISTS idx_omen_signals_type 
                    ON omen_signals(signal_type);
            """)
            logger.info("PostgreSQL tables created/verified")

    def _ensure_initialized(self) -> None:
        """Ensure repository is initialized."""
        if not self._initialized:
            raise RuntimeError(
                "PostgreSQL repository not initialized. Call await initialize() first."
            )

    # === Sync interface (SignalRepository) ===

    def save(self, signal: OmenSignal) -> None:
        """
        Sync save - wraps async version.
        For production, prefer async methods.
        """
        import asyncio

        asyncio.get_event_loop().run_until_complete(self.save_async(signal))

    def find_by_id(self, signal_id: str) -> Optional[OmenSignal]:
        """Sync find by ID."""
        import asyncio

        return asyncio.get_event_loop().run_until_complete(self.find_by_id_async(signal_id))

    def find_by_hash(self, input_event_hash: str) -> Optional[OmenSignal]:
        """Sync find by hash."""
        import asyncio

        return asyncio.get_event_loop().run_until_complete(
            self.find_by_hash_async(input_event_hash)
        )

    def find_by_event_id(self, event_id: str) -> list[OmenSignal]:
        """Sync find by event ID."""
        import asyncio

        return asyncio.get_event_loop().run_until_complete(self._find_by_event_id_async(event_id))

    def find_recent(
        self,
        limit: int = 100,
        offset: int = 0,
        since: Optional[datetime] = None,
    ) -> list[OmenSignal]:
        """Sync find recent."""
        import asyncio

        return asyncio.get_event_loop().run_until_complete(
            self.find_recent_async(limit=limit, since=since)
        )

    def count(self, since: Optional[datetime] = None) -> int:
        """Sync count."""
        import asyncio

        return asyncio.get_event_loop().run_until_complete(self._count_async(since))

    # === Async interface (AsyncSignalRepository) ===

    async def save_async(self, signal: OmenSignal) -> None:
        """
        Persist signal to PostgreSQL with UPSERT.
        Idempotent - same signal_id will update existing record.
        """
        self._ensure_initialized()

        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO omen_signals (
                    signal_id, source_event_id, trace_id, input_event_hash,
                    title, description, probability, confidence_score,
                    confidence_level, signal_type, status, category,
                    tags, geographic, temporal, evidence, payload, generated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, 
                          $13, $14, $15, $16, $17, $18)
                ON CONFLICT (signal_id) DO UPDATE SET
                    payload = EXCLUDED.payload,
                    updated_at = NOW()
            """,
                signal.signal_id,
                signal.source_event_id,
                getattr(signal, "trace_id", None),
                getattr(signal, "input_event_hash", None),
                signal.title,
                getattr(signal, "description", None),
                signal.probability,
                signal.confidence_score,
                signal.confidence_level.value if signal.confidence_level else None,
                signal.signal_type.value if signal.signal_type else None,
                signal.status.value if signal.status else None,
                signal.category.value if signal.category else None,
                json.dumps(list(signal.tags) if signal.tags else []),
                json.dumps(signal.geographic.model_dump()) if signal.geographic else None,
                json.dumps(signal.temporal.model_dump()) if signal.temporal else None,
                json.dumps([e.model_dump() for e in signal.evidence] if signal.evidence else []),
                signal.model_dump_json(),
                signal.generated_at,
            )
            logger.debug("Saved signal %s to PostgreSQL", signal.signal_id)

    async def find_by_id_async(self, signal_id: str) -> Optional[OmenSignal]:
        """Find signal by ID."""
        self._ensure_initialized()

        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT payload FROM omen_signals WHERE signal_id = $1", signal_id
            )
            if row:
                return OmenSignal.model_validate_json(row["payload"])
            return None

    async def find_by_hash_async(self, input_event_hash: str) -> Optional[OmenSignal]:
        """Find signal by input event hash (idempotency check)."""
        self._ensure_initialized()

        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT payload FROM omen_signals WHERE input_event_hash = $1", input_event_hash
            )
            if row:
                return OmenSignal.model_validate_json(row["payload"])
            return None

    async def _find_by_event_id_async(self, event_id: str) -> list[OmenSignal]:
        """Find all signals from a source event."""
        self._ensure_initialized()

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT payload FROM omen_signals WHERE source_event_id = $1 ORDER BY generated_at DESC",
                event_id,
            )
            return [OmenSignal.model_validate_json(row["payload"]) for row in rows]

    async def find_recent_async(
        self,
        limit: int = 100,
        since: Optional[datetime] = None,
    ) -> list[OmenSignal]:
        """Find recent signals."""
        self._ensure_initialized()

        query = "SELECT payload FROM omen_signals"
        params = []

        if since:
            params.append(since)
            query += " WHERE generated_at >= $1"

        query += " ORDER BY generated_at DESC LIMIT $" + str(len(params) + 1)
        params.append(limit)

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
            return [OmenSignal.model_validate_json(row["payload"]) for row in rows]

    async def _count_async(self, since: Optional[datetime] = None) -> int:
        """Count signals."""
        self._ensure_initialized()

        async with self._pool.acquire() as conn:
            if since:
                result = await conn.fetchval(
                    "SELECT COUNT(*) FROM omen_signals WHERE generated_at >= $1", since
                )
            else:
                result = await conn.fetchval("SELECT COUNT(*) FROM omen_signals")
            return result or 0

    async def exists(self, input_event_hash: str) -> bool:
        """Check if signal with hash exists (fast idempotency check)."""
        self._ensure_initialized()

        async with self._pool.acquire() as conn:
            result = await conn.fetchval(
                "SELECT EXISTS(SELECT 1 FROM omen_signals WHERE input_event_hash = $1)",
                input_event_hash,
            )
            return result

    async def close(self) -> None:
        """Close connection pool."""
        if self._pool:
            await self._pool.close()
            logger.info("PostgreSQL connection pool closed")


# Factory function for easy creation
async def create_postgres_repository(
    dsn: str,
    min_pool_size: int = 5,
    max_pool_size: int = 20,
) -> PostgresSignalRepository:
    """Create and initialize a PostgreSQL repository."""
    repo = PostgresSignalRepository(dsn, min_pool_size, max_pool_size)
    await repo.initialize()
    return repo
