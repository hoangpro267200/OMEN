"""
Database Migration System

Manages SQLite schema migrations with version tracking.
"""

import hashlib
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import aiosqlite

logger = logging.getLogger(__name__)


@dataclass
class Migration:
    """Database migration definition."""

    version: int
    description: str
    up_sql: str
    down_sql: str | None = None


class MigrationRunner:
    """
    Runs database migrations with tracking.

    Usage:
        runner = MigrationRunner(db_path, migrations)
        await runner.run()
    """

    MIGRATIONS_TABLE_SQL = """
    CREATE TABLE IF NOT EXISTS _schema_migrations (
        version INTEGER PRIMARY KEY,
        description TEXT NOT NULL,
        applied_at TEXT NOT NULL,
        checksum TEXT
    )
    """

    def __init__(
        self,
        db_path: str | Path,
        migrations: list[Migration],
    ) -> None:
        self.db_path = Path(db_path)
        self.migrations = sorted(migrations, key=lambda m: m.version)

    async def run(self) -> list[int]:
        """
        Apply pending migrations.

        Returns:
            List of applied migration versions
        """
        applied: list[int] = []
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(self.MIGRATIONS_TABLE_SQL)
            await db.commit()

            cursor = await db.execute("SELECT version FROM _schema_migrations ORDER BY version")
            rows = await cursor.fetchall()
            applied_versions = {row[0] for row in rows}

            for migration in self.migrations:
                if migration.version in applied_versions:
                    continue

                logger.info(
                    "Applying migration %s: %s",
                    migration.version,
                    migration.description,
                )

                try:
                    await db.executescript(migration.up_sql)
                    await db.execute(
                        """
                        INSERT INTO _schema_migrations
                        (version, description, applied_at, checksum)
                        VALUES (?, ?, ?, ?)
                        """,
                        (
                            migration.version,
                            migration.description,
                            datetime.now(timezone.utc).isoformat() + "Z",
                            self._checksum(migration.up_sql),
                        ),
                    )
                    await db.commit()
                    applied.append(migration.version)
                    logger.info(
                        "Migration %s applied successfully",
                        migration.version,
                    )
                except Exception as e:
                    logger.error(
                        "Migration %s failed: %s",
                        migration.version,
                        e,
                    )
                    await db.rollback()
                    raise

        return applied

    async def rollback(self, target_version: int) -> list[int]:
        """
        Rollback to target version.

        Returns:
            List of rolled back migration versions
        """
        rolled_back: list[int] = []

        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT version FROM _schema_migrations WHERE version > ? ORDER BY version DESC",
                (target_version,),
            )
            rows = await cursor.fetchall()
            versions_to_rollback = [row[0] for row in rows]

            for version in versions_to_rollback:
                migration = next(
                    (m for m in self.migrations if m.version == version),
                    None,
                )
                if not migration or not migration.down_sql:
                    raise ValueError(f"Cannot rollback migration {version}: no down_sql defined")
                logger.info("Rolling back migration %s", version)
                await db.executescript(migration.down_sql)
                await db.execute(
                    "DELETE FROM _schema_migrations WHERE version = ?",
                    (version,),
                )
                await db.commit()
                rolled_back.append(version)

        return rolled_back

    async def get_current_version(self) -> int:
        """Get current schema version."""
        if not self.db_path.exists():
            return 0
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(self.MIGRATIONS_TABLE_SQL)
            await db.commit()
            cursor = await db.execute("SELECT MAX(version) FROM _schema_migrations")
            row = await cursor.fetchone()
            return row[0] or 0

    async def get_pending_migrations(self) -> list[Migration]:
        """Get list of pending migrations."""
        current = await self.get_current_version()
        return [m for m in self.migrations if m.version > current]

    @staticmethod
    def _checksum(sql: str) -> str:
        """Calculate checksum of migration SQL."""
        return hashlib.md5(sql.encode()).hexdigest()[:8]


# ═══════════════════════════════════════════════════════════════════════════════
# RiskCast Migrations
# ═══════════════════════════════════════════════════════════════════════════════

RISKCAST_MIGRATIONS = [
    Migration(
        version=1,
        description="Initial schema - processed_signals table",
        up_sql="""
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
        );

        CREATE INDEX IF NOT EXISTS idx_partition_date
            ON processed_signals(partition_date);
        CREATE INDEX IF NOT EXISTS idx_trace_id
            ON processed_signals(trace_id);
        CREATE INDEX IF NOT EXISTS idx_source
            ON processed_signals(source);
        """,
        down_sql="DROP TABLE IF EXISTS processed_signals;",
    ),
    Migration(
        version=2,
        description="Add reconcile_state table",
        up_sql="""
        CREATE TABLE IF NOT EXISTS reconcile_state (
            partition_date TEXT PRIMARY KEY,
            last_reconcile_at TEXT NOT NULL,
            ledger_highwater INTEGER NOT NULL,
            manifest_revision INTEGER NOT NULL,
            ledger_record_count INTEGER NOT NULL,
            processed_count INTEGER NOT NULL,
            missing_count INTEGER NOT NULL,
            status TEXT NOT NULL,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        """,
        down_sql="DROP TABLE IF EXISTS reconcile_state;",
    ),
    Migration(
        version=3,
        description="Add category index for analytics",
        up_sql="""
        -- SQLite 3.31+: VIRTUAL generated column (STORED not allowed in ALTER TABLE)
        ALTER TABLE processed_signals
            ADD COLUMN category TEXT
            GENERATED ALWAYS AS (json_extract(signal_data, '$.signal.category'));
        CREATE INDEX IF NOT EXISTS idx_category ON processed_signals(category);
        """,
        down_sql="""
        DROP INDEX IF EXISTS idx_category;
        """,
    ),
    Migration(
        version=4,
        description="Add severity column for filtering",
        up_sql="""
        ALTER TABLE processed_signals
            ADD COLUMN severity TEXT DEFAULT 'MEDIUM';
        CREATE INDEX IF NOT EXISTS idx_severity ON processed_signals(severity);
        """,
        down_sql="""
        DROP INDEX IF EXISTS idx_severity;
        """,
    ),
]


async def run_riskcast_migrations(db_path: str | Path) -> list[int]:
    """Run all RiskCast migrations. Returns list of applied versions."""
    runner = MigrationRunner(db_path, RISKCAST_MIGRATIONS)
    applied = await runner.run()
    if applied:
        logger.info("Applied %s migrations: %s", len(applied), applied)
    else:
        logger.info("Database is up to date")
    return applied
