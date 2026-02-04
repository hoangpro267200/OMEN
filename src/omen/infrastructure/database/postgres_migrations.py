"""
PostgreSQL Migration System for OMEN Persistence Layer.

Manages versioned schema migrations with tracking, rollback support,
and checksum validation. Separate from SQLite migrations used by RiskCast.

Usage:
    runner = PostgresMigrationRunner(pool)
    await runner.run()  # Apply all pending migrations
"""

from __future__ import annotations

import hashlib
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class PostgresMigration:
    """PostgreSQL migration definition."""

    version: str  # e.g., "V1_0_0"
    description: str
    up_sql: str
    down_sql: Optional[str] = None

    @property
    def version_tuple(self) -> tuple[int, int, int]:
        """Parse version string to tuple for sorting."""
        match = re.match(r"V(\d+)_(\d+)_(\d+)", self.version)
        if not match:
            raise ValueError(f"Invalid version format: {self.version}")
        return (int(match.group(1)), int(match.group(2)), int(match.group(3)))


class PostgresMigrationRunner:
    """
    Runs PostgreSQL migrations with version tracking.

    Features:
    - Versioned migrations (V1_0_0 format)
    - Checksum validation
    - Rollback support
    - Transaction-safe execution
    - Audit logging of migrations

    Usage:
        async with asyncpg.create_pool(dsn) as pool:
            runner = PostgresMigrationRunner(pool)
            applied = await runner.run()
    """

    MIGRATIONS_TABLE_SQL = """
    CREATE TABLE IF NOT EXISTS _schema_migrations (
        version VARCHAR(32) PRIMARY KEY,
        description TEXT NOT NULL,
        applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        checksum VARCHAR(16) NOT NULL,
        execution_time_ms INTEGER,
        applied_by VARCHAR(128) DEFAULT CURRENT_USER
    );
    """

    def __init__(
        self,
        pool,
        migrations: Optional[list[PostgresMigration]] = None,
        migrations_dir: Optional[Path] = None,
    ) -> None:
        """
        Initialize migration runner.

        Args:
            pool: asyncpg connection pool
            migrations: List of migration objects (takes precedence)
            migrations_dir: Directory containing .sql migration files
        """
        self._pool = pool
        self._migrations_dir = migrations_dir or Path(__file__).parent / "migrations"

        if migrations:
            self.migrations = sorted(migrations, key=lambda m: m.version_tuple)
        else:
            self.migrations = self._load_migrations_from_dir()

    def _load_migrations_from_dir(self) -> list[PostgresMigration]:
        """Load migrations from SQL files in migrations directory."""
        migrations = []

        if not self._migrations_dir.exists():
            logger.warning("Migrations directory does not exist: %s", self._migrations_dir)
            return migrations

        for sql_file in sorted(self._migrations_dir.glob("V*__*.sql")):
            # Parse filename: V1_0_0__description.sql
            match = re.match(r"(V\d+_\d+_\d+)__(.+)\.sql", sql_file.name)
            if not match:
                logger.warning("Skipping invalid migration filename: %s", sql_file.name)
                continue

            version = match.group(1)
            description = match.group(2).replace("_", " ")
            up_sql = sql_file.read_text(encoding="utf-8")

            # Check for corresponding rollback file
            down_file = sql_file.with_suffix(".down.sql")
            down_sql = down_file.read_text(encoding="utf-8") if down_file.exists() else None

            migrations.append(
                PostgresMigration(
                    version=version,
                    description=description,
                    up_sql=up_sql,
                    down_sql=down_sql,
                )
            )

        return sorted(migrations, key=lambda m: m.version_tuple)

    async def run(self) -> list[str]:
        """
        Apply all pending migrations.

        Returns:
            List of applied migration versions

        Raises:
            Exception: If any migration fails (rolls back that migration)
        """
        applied: list[str] = []

        async with self._pool.acquire() as conn:
            # Ensure migrations table exists
            await conn.execute(self.MIGRATIONS_TABLE_SQL)

            # Get already applied migrations
            rows = await conn.fetch(
                "SELECT version FROM _schema_migrations ORDER BY version"
            )
            applied_versions = {row["version"] for row in rows}

            for migration in self.migrations:
                if migration.version in applied_versions:
                    continue

                logger.info(
                    "Applying migration %s: %s",
                    migration.version,
                    migration.description,
                )

                start_time = datetime.now(timezone.utc)

                try:
                    # Execute migration in a transaction
                    async with conn.transaction():
                        await conn.execute(migration.up_sql)

                        execution_time_ms = int(
                            (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
                        )

                        await conn.execute(
                            """
                            INSERT INTO _schema_migrations
                            (version, description, applied_at, checksum, execution_time_ms)
                            VALUES ($1, $2, $3, $4, $5)
                            """,
                            migration.version,
                            migration.description,
                            datetime.now(timezone.utc),
                            self._checksum(migration.up_sql),
                            execution_time_ms,
                        )

                    applied.append(migration.version)
                    logger.info(
                        "Migration %s applied successfully in %dms",
                        migration.version,
                        execution_time_ms,
                    )

                except Exception as e:
                    logger.error(
                        "Migration %s failed: %s",
                        migration.version,
                        e,
                    )
                    raise

        if applied:
            logger.info("Applied %d migrations: %s", len(applied), applied)
        else:
            logger.info("Database schema is up to date")

        return applied

    async def rollback(self, target_version: str) -> list[str]:
        """
        Rollback migrations to target version.

        Args:
            target_version: Version to rollback to (exclusive - this version stays)

        Returns:
            List of rolled back migration versions

        Raises:
            ValueError: If migration has no down_sql defined
        """
        rolled_back: list[str] = []

        async with self._pool.acquire() as conn:
            # Get migrations to rollback (newer than target)
            rows = await conn.fetch(
                """
                SELECT version FROM _schema_migrations 
                WHERE version > $1 
                ORDER BY version DESC
                """,
                target_version,
            )
            versions_to_rollback = [row["version"] for row in rows]

            for version in versions_to_rollback:
                migration = next(
                    (m for m in self.migrations if m.version == version),
                    None,
                )

                if not migration:
                    raise ValueError(f"Migration {version} not found in migrations list")

                if not migration.down_sql:
                    raise ValueError(
                        f"Cannot rollback migration {version}: no down_sql defined"
                    )

                logger.info("Rolling back migration %s", version)

                async with conn.transaction():
                    await conn.execute(migration.down_sql)
                    await conn.execute(
                        "DELETE FROM _schema_migrations WHERE version = $1",
                        version,
                    )

                rolled_back.append(version)
                logger.info("Rolled back migration %s", version)

        return rolled_back

    async def get_current_version(self) -> Optional[str]:
        """Get the current (latest applied) schema version."""
        async with self._pool.acquire() as conn:
            await conn.execute(self.MIGRATIONS_TABLE_SQL)
            row = await conn.fetchrow(
                "SELECT version FROM _schema_migrations ORDER BY version DESC LIMIT 1"
            )
            return row["version"] if row else None

    async def get_pending_migrations(self) -> list[PostgresMigration]:
        """Get list of migrations that haven't been applied yet."""
        current = await self.get_current_version()

        if current is None:
            return self.migrations

        current_tuple = PostgresMigration(
            version=current, description="", up_sql=""
        ).version_tuple

        return [m for m in self.migrations if m.version_tuple > current_tuple]

    async def get_migration_history(self) -> list[dict]:
        """Get full migration history with timestamps."""
        async with self._pool.acquire() as conn:
            await conn.execute(self.MIGRATIONS_TABLE_SQL)
            rows = await conn.fetch(
                """
                SELECT version, description, applied_at, checksum, 
                       execution_time_ms, applied_by
                FROM _schema_migrations 
                ORDER BY version
                """
            )
            return [dict(row) for row in rows]

    async def verify_checksums(self) -> list[tuple[str, str, str]]:
        """
        Verify that applied migrations match current files.

        Returns:
            List of (version, expected_checksum, actual_checksum) for mismatches
        """
        mismatches = []

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT version, checksum FROM _schema_migrations"
            )
            applied_checksums = {row["version"]: row["checksum"] for row in rows}

        for migration in self.migrations:
            if migration.version in applied_checksums:
                expected = applied_checksums[migration.version]
                actual = self._checksum(migration.up_sql)
                if expected != actual:
                    mismatches.append((migration.version, expected, actual))

        return mismatches

    @staticmethod
    def _checksum(sql: str) -> str:
        """Calculate checksum of migration SQL."""
        # Normalize whitespace for consistent checksums
        normalized = " ".join(sql.split())
        return hashlib.md5(normalized.encode()).hexdigest()[:16]


async def run_postgres_migrations(dsn: str) -> list[str]:
    """
    Convenience function to run all PostgreSQL migrations.

    Args:
        dsn: PostgreSQL connection string

    Returns:
        List of applied migration versions
    """
    try:
        import asyncpg
    except ImportError:
        raise ImportError(
            "asyncpg is required for PostgreSQL migrations. "
            "Install with: pip install asyncpg"
        )

    pool = await asyncpg.create_pool(dsn, min_size=1, max_size=2)
    try:
        runner = PostgresMigrationRunner(pool)
        return await runner.run()
    finally:
        await pool.close()


# CLI entry point
if __name__ == "__main__":
    import asyncio
    import os
    import sys

    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        print("ERROR: DATABASE_URL environment variable not set", file=sys.stderr)
        sys.exit(1)

    async def main():
        applied = await run_postgres_migrations(dsn)
        if applied:
            print(f"Applied {len(applied)} migrations: {applied}")
        else:
            print("Database is up to date")

    asyncio.run(main())
