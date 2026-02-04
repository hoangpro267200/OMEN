"""
PostgreSQL-backed Signal Repository.

Enables horizontal scaling and persistent storage.
Production-ready implementation with connection pooling.

PERSISTENCE ARCHITECTURE (v2.0):
- Supports 4-schema architecture: demo, live, audit, system
- Schema routing based on source attestation (REAL/MOCK/HYBRID)
- All write operations logged to audit.operation_log
- MOCK data NEVER goes to live schema
- live schema requires REAL attestation with api_response_hash
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Optional, TYPE_CHECKING
from uuid import UUID

from ...application.ports.signal_repository import SignalRepository, AsyncSignalRepository
from ...domain.models.omen_signal import OmenSignal
from ...domain.models.attestation import (
    SignalAttestation,
    SourceType,
    AttestationStatus,
)
from .schema_router import (
    Schema,
    SchemaRouter,
    GateStatus,
    GateCheckResult,
    RoutingDecision,
    determine_schema,
)
from .audit_logger import AuditLogger, log_attestation

if TYPE_CHECKING:
    import asyncpg

logger = logging.getLogger(__name__)


class PostgresSignalRepository(SignalRepository):
    """
    Production-ready PostgreSQL repository with schema routing.

    Supports:
    - Connection pooling via asyncpg
    - Async operations
    - Horizontal scaling (multiple instances)
    - UPSERT for idempotency
    - Schema routing (demo/live) based on attestation
    - Audit logging for all write operations

    Requires:
    - asyncpg library: pip install asyncpg
    - PostgreSQL 15+

    Schema Routing:
    - MOCK signals → demo.signals (always)
    - HYBRID signals → demo.signals (treated as MOCK)
    - REAL signals → live.signals (if gate allowed) or demo.signals
    """

    def __init__(
        self,
        dsn: str,
        min_pool_size: int = 5,
        max_pool_size: int = 20,
        use_schema_routing: bool = True,
    ):
        """
        Initialize PostgreSQL repository.

        Args:
            dsn: PostgreSQL connection string (e.g., "postgresql://user:pass@host:5432/db")
            min_pool_size: Minimum connections in pool
            max_pool_size: Maximum connections in pool
            use_schema_routing: If True, use new 4-schema architecture.
                              If False, use legacy single-table mode for backward compatibility.
        """
        self.dsn = dsn
        self.min_pool_size = min_pool_size
        self.max_pool_size = max_pool_size
        self.use_schema_routing = use_schema_routing
        self._pool: Optional["asyncpg.Pool"] = None
        self._initialized = False
        self._schema_router = SchemaRouter()

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

    # ═══════════════════════════════════════════════════════════════════════════
    # Schema-Aware Methods (v2.0)
    # ═══════════════════════════════════════════════════════════════════════════

    async def save_with_attestation(
        self,
        signal: OmenSignal,
        attestation: SignalAttestation,
        gate_result: Optional[GateCheckResult] = None,
        trace_id: Optional[str] = None,
        performed_by: Optional[str] = None,
    ) -> RoutingDecision:
        """
        Save signal with source attestation and schema routing.

        This is the preferred method for production use. It:
        1. Determines the target schema based on attestation
        2. Persists the signal to the appropriate schema
        3. Logs the operation to audit.operation_log
        4. Logs the attestation to audit.source_attestations

        Args:
            signal: The signal to persist
            attestation: Source attestation (determines schema routing)
            gate_result: Optional pre-computed gate check result
            trace_id: Request trace ID for audit trail
            performed_by: Who/what is performing the operation

        Returns:
            RoutingDecision with target schema and reasoning

        Raises:
            RuntimeError: If repository not initialized
        """
        self._ensure_initialized()

        # Determine target schema
        decision = self._schema_router.route(attestation, gate_result)
        schema = decision.schema.value
        table = f"{schema}.signals"

        async with self._pool.acquire() as conn:
            async with conn.transaction():
                # Check if signal already exists (for audit logging)
                existing = await conn.fetchrow(
                    f"SELECT signal_id, payload FROM {table} WHERE signal_id = $1",
                    signal.signal_id,
                )
                old_value = json.loads(existing["payload"]) if existing else None

                # Persist to schema-specific table
                await conn.execute(
                    f"""
                    INSERT INTO {table} (
                        signal_id, source_event_id, trace_id, input_event_hash,
                        source_type, attestation_id,
                        title, description, probability, confidence_score,
                        confidence_level, signal_type, status, category,
                        tags, geographic, temporal, evidence, payload,
                        generated_at, ingested_from, api_response_hash
                    ) VALUES (
                        $1, $2, $3, $4,
                        $5::source_type, $6,
                        $7, $8, $9, $10,
                        $11, $12, $13, $14,
                        $15, $16, $17, $18, $19,
                        $20, $21, $22
                    )
                    ON CONFLICT (signal_id) DO UPDATE SET
                        payload = EXCLUDED.payload,
                        source_type = EXCLUDED.source_type,
                        attestation_id = EXCLUDED.attestation_id,
                        updated_at = NOW()
                    """,
                    signal.signal_id,
                    signal.source_event_id,
                    trace_id or getattr(signal, "trace_id", None),
                    getattr(signal, "input_event_hash", None),
                    attestation.source_type.value,
                    attestation.id,
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
                    attestation.source_id,
                    attestation.api_response_hash,
                )

                # Log attestation to audit schema
                await log_attestation(conn, attestation)

                # Log operation to audit schema
                audit_logger = AuditLogger(conn)
                await audit_logger.log_upsert(
                    schema=schema,
                    table="signals",
                    record_id=signal.signal_id,
                    new_value=json.loads(signal.model_dump_json()),
                    old_value=old_value,
                    attestation_id=attestation.id,
                    source_type=attestation.source_type.value,
                    trace_id=trace_id,
                    performed_by=performed_by or "system",
                    reason=f"Signal ingestion from {attestation.source_id}",
                )

        logger.info(
            "Saved signal %s to %s (source_type=%s)",
            signal.signal_id,
            table,
            attestation.source_type.value,
        )
        return decision

    async def find_by_id_in_schema(
        self,
        signal_id: str,
        schema: Schema = Schema.DEMO,
    ) -> Optional[OmenSignal]:
        """
        Find signal by ID in a specific schema.

        Args:
            signal_id: Signal ID to find
            schema: Schema to search (default: demo)

        Returns:
            OmenSignal if found, None otherwise
        """
        self._ensure_initialized()

        table = f"{schema.value}.signals"

        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                f"SELECT payload FROM {table} WHERE signal_id = $1",
                signal_id,
            )
            if row:
                return OmenSignal.model_validate_json(row["payload"])
            return None

    async def find_recent_in_schema(
        self,
        schema: Schema = Schema.DEMO,
        limit: int = 100,
        offset: int = 0,
        source_type: Optional[SourceType] = None,
        signal_type: Optional[str] = None,
        since: Optional[datetime] = None,
    ) -> list[OmenSignal]:
        """
        Find recent signals in a specific schema with filters.

        Args:
            schema: Schema to search (default: demo)
            limit: Maximum number of results
            offset: Number of results to skip
            source_type: Filter by source type (REAL, MOCK, HYBRID)
            signal_type: Filter by signal type
            since: Only signals after this timestamp

        Returns:
            List of matching signals
        """
        self._ensure_initialized()

        table = f"{schema.value}.signals"

        # Build query with filters
        conditions = []
        params = []
        param_idx = 1

        if source_type:
            conditions.append(f"source_type = ${param_idx}::source_type")
            params.append(source_type.value)
            param_idx += 1

        if signal_type:
            conditions.append(f"signal_type = ${param_idx}")
            params.append(signal_type)
            param_idx += 1

        if since:
            conditions.append(f"generated_at >= ${param_idx}")
            params.append(since)
            param_idx += 1

        where_clause = ""
        if conditions:
            where_clause = "WHERE " + " AND ".join(conditions)

        query = f"""
            SELECT payload FROM {table}
            {where_clause}
            ORDER BY generated_at DESC
            LIMIT ${param_idx} OFFSET ${param_idx + 1}
        """
        params.extend([limit, offset])

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
            return [OmenSignal.model_validate_json(row["payload"]) for row in rows]

    async def count_in_schema(
        self,
        schema: Schema = Schema.DEMO,
        source_type: Optional[SourceType] = None,
        since: Optional[datetime] = None,
    ) -> int:
        """
        Count signals in a specific schema.

        Args:
            schema: Schema to count (default: demo)
            source_type: Filter by source type
            since: Only count signals after this timestamp

        Returns:
            Number of matching signals
        """
        self._ensure_initialized()

        table = f"{schema.value}.signals"

        conditions = []
        params = []
        param_idx = 1

        if source_type:
            conditions.append(f"source_type = ${param_idx}::source_type")
            params.append(source_type.value)
            param_idx += 1

        if since:
            conditions.append(f"generated_at >= ${param_idx}")
            params.append(since)
            param_idx += 1

        where_clause = ""
        if conditions:
            where_clause = "WHERE " + " AND ".join(conditions)

        query = f"SELECT COUNT(*) FROM {table} {where_clause}"

        async with self._pool.acquire() as conn:
            result = await conn.fetchval(query, *params)
            return result or 0

    async def get_schema_stats(self) -> dict:
        """
        Get statistics for all schemas.

        Returns:
            Dictionary with counts per schema and source type
        """
        self._ensure_initialized()

        stats = {
            "demo": {"total": 0, "real": 0, "mock": 0, "hybrid": 0},
            "live": {"total": 0, "real": 0},
        }

        async with self._pool.acquire() as conn:
            # Demo schema stats
            demo_stats = await conn.fetch("""
                SELECT source_type, COUNT(*) as count
                FROM demo.signals
                GROUP BY source_type
            """)
            for row in demo_stats:
                source_type = row["source_type"].lower() if row["source_type"] else "mock"
                stats["demo"][source_type] = row["count"]
                stats["demo"]["total"] += row["count"]

            # Live schema stats
            live_stats = await conn.fetch("""
                SELECT source_type, COUNT(*) as count
                FROM live.signals
                GROUP BY source_type
            """)
            for row in live_stats:
                source_type = row["source_type"].lower() if row["source_type"] else "real"
                stats["live"][source_type] = row["count"]
                stats["live"]["total"] += row["count"]

        return stats

    async def run_migrations(self) -> list[str]:
        """
        Run pending PostgreSQL migrations.

        Returns:
            List of applied migration versions
        """
        from ..infrastructure.database.postgres_migrations import PostgresMigrationRunner

        runner = PostgresMigrationRunner(self._pool)
        return await runner.run()


# Factory function for easy creation
async def create_postgres_repository(
    dsn: str,
    min_pool_size: int = 5,
    max_pool_size: int = 20,
    use_schema_routing: bool = True,
) -> PostgresSignalRepository:
    """
    Create and initialize a PostgreSQL repository.

    Args:
        dsn: PostgreSQL connection string
        min_pool_size: Minimum connections in pool
        max_pool_size: Maximum connections in pool
        use_schema_routing: If True, use 4-schema architecture

    Returns:
        Initialized PostgresSignalRepository
    """
    repo = PostgresSignalRepository(
        dsn,
        min_pool_size,
        max_pool_size,
        use_schema_routing=use_schema_routing,
    )
    await repo.initialize()
    return repo


async def create_schema_aware_repository(
    dsn: Optional[str] = None,
    min_pool_size: int = 5,
    max_pool_size: int = 20,
) -> PostgresSignalRepository:
    """
    Create a PostgreSQL repository with schema routing enabled.

    This is the recommended factory for production use.

    Args:
        dsn: PostgreSQL connection string (defaults to DATABASE_URL env var)
        min_pool_size: Minimum connections in pool
        max_pool_size: Maximum connections in pool

    Returns:
        Initialized PostgresSignalRepository with schema routing

    Raises:
        ValueError: If no DSN provided and DATABASE_URL not set
    """
    if dsn is None:
        dsn = os.environ.get("DATABASE_URL")
        if not dsn:
            raise ValueError(
                "No database DSN provided and DATABASE_URL environment variable not set"
            )

    return await create_postgres_repository(
        dsn,
        min_pool_size=min_pool_size,
        max_pool_size=max_pool_size,
        use_schema_routing=True,
    )
