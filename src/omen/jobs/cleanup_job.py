"""
Database Cleanup Job for Data Retention.

Automatically deletes old data based on retention policies:
- demo.raw_inputs: 72 hours
- demo.ingestion_logs: 30 days
- audit.api_access_log: 90 days

Usage:
    # Run specific job
    python -m omen.jobs.cleanup_job --job raw_inputs --dry-run
    python -m omen.jobs.cleanup_job --job raw_inputs

    # Run all jobs
    python -m omen.jobs.cleanup_job --all
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class CleanupConfig:
    """Configuration for a cleanup job."""

    table: str
    retention_hours: Optional[int] = None
    retention_days: Optional[int] = None
    timestamp_column: str = "created_at"
    batch_size: int = 1000  # Delete in batches to avoid table locks
    description: str = ""

    @property
    def retention_description(self) -> str:
        """Human-readable retention description."""
        if self.retention_hours:
            return f"{self.retention_hours} hours"
        if self.retention_days:
            return f"{self.retention_days} days"
        return "unknown"


@dataclass
class CleanupResult:
    """Result of a cleanup operation."""

    job_name: str
    table: str
    status: str  # SUCCESS, FAILED, DRY_RUN
    rows_affected: int
    duration_ms: int
    cutoff_timestamp: datetime
    dry_run: bool
    error_message: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "job_name": self.job_name,
            "table": self.table,
            "status": self.status,
            "rows_affected": self.rows_affected,
            "duration_ms": self.duration_ms,
            "cutoff_timestamp": self.cutoff_timestamp.isoformat(),
            "dry_run": self.dry_run,
            "error_message": self.error_message,
        }


class CleanupJob:
    """
    Database cleanup job with batch deletion.

    Features:
    - Batch deletion to avoid table locks
    - Dry-run mode for testing
    - Audit logging
    - Graceful error handling
    """

    def __init__(
        self,
        name: str,
        config: CleanupConfig,
        db_pool: Any,
    ):
        """
        Initialize cleanup job.

        Args:
            name: Job name (for logging and audit)
            config: Cleanup configuration
            db_pool: asyncpg connection pool
        """
        self.name = name
        self.config = config
        self._pool = db_pool

    async def run(self, dry_run: bool = False) -> CleanupResult:
        """
        Run the cleanup job.

        Args:
            dry_run: If True, only count rows without deleting

        Returns:
            CleanupResult with operation details
        """
        cutoff = self._calculate_cutoff()
        start_time = datetime.now(timezone.utc)

        logger.info(
            "Cleanup job '%s' starting: table=%s, cutoff=%s, dry_run=%s",
            self.name,
            self.config.table,
            cutoff.isoformat(),
            dry_run,
        )

        try:
            # Count rows to delete
            count_query = f"""
                SELECT COUNT(*) FROM {self.config.table}
                WHERE {self.config.timestamp_column} < $1
            """
            async with self._pool.acquire() as conn:
                total_count = await conn.fetchval(count_query, cutoff)

            logger.info(
                "Cleanup job '%s': found %d rows older than %s",
                self.name,
                total_count,
                cutoff.isoformat(),
            )

            if dry_run:
                duration_ms = int(
                    (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
                )
                return CleanupResult(
                    job_name=self.name,
                    table=self.config.table,
                    status="DRY_RUN",
                    rows_affected=total_count,
                    duration_ms=duration_ms,
                    cutoff_timestamp=cutoff,
                    dry_run=True,
                )

            # Delete in batches
            deleted = 0
            delete_query = f"""
                DELETE FROM {self.config.table}
                WHERE ctid IN (
                    SELECT ctid FROM {self.config.table}
                    WHERE {self.config.timestamp_column} < $1
                    LIMIT {self.config.batch_size}
                )
            """

            while deleted < total_count:
                async with self._pool.acquire() as conn:
                    result = await conn.execute(delete_query, cutoff)
                    # Parse result like "DELETE 1000"
                    batch_deleted = int(result.split()[-1])
                    deleted += batch_deleted

                    if batch_deleted < self.config.batch_size:
                        break  # No more rows to delete

                    # Brief pause between batches to reduce lock contention
                    await asyncio.sleep(0.1)

            duration_ms = int(
                (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            )

            # Log to audit table
            await self._log_cleanup_audit(deleted, cutoff, duration_ms)

            logger.info(
                "Cleanup job '%s' completed: deleted %d rows in %dms",
                self.name,
                deleted,
                duration_ms,
            )

            return CleanupResult(
                job_name=self.name,
                table=self.config.table,
                status="SUCCESS",
                rows_affected=deleted,
                duration_ms=duration_ms,
                cutoff_timestamp=cutoff,
                dry_run=False,
            )

        except Exception as e:
            duration_ms = int(
                (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            )
            logger.error("Cleanup job '%s' failed: %s", self.name, e)

            return CleanupResult(
                job_name=self.name,
                table=self.config.table,
                status="FAILED",
                rows_affected=0,
                duration_ms=duration_ms,
                cutoff_timestamp=cutoff,
                dry_run=dry_run,
                error_message=str(e),
            )

    def _calculate_cutoff(self) -> datetime:
        """Calculate the cutoff timestamp based on retention policy."""
        now = datetime.now(timezone.utc)
        if self.config.retention_hours:
            return now - timedelta(hours=self.config.retention_hours)
        if self.config.retention_days:
            return now - timedelta(days=self.config.retention_days)
        raise ValueError(
            f"Job '{self.name}': must specify retention_hours or retention_days"
        )

    async def _log_cleanup_audit(
        self,
        rows_deleted: int,
        cutoff: datetime,
        duration_ms: int,
    ) -> None:
        """Log cleanup operation to system.cleanup_log."""
        try:
            async with self._pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO system.cleanup_log (
                        job_name, job_type, target_schema, target_table,
                        started_at, completed_at, duration_ms,
                        status, rows_affected, cutoff_timestamp,
                        retention_hours, triggered_by
                    ) VALUES (
                        $1, 'CLEANUP', $2, $3,
                        $4, $5, $6,
                        'SUCCESS', $7, $8,
                        $9, 'SCHEDULER'
                    )
                    """,
                    self.name,
                    self.config.table.split(".")[0],  # schema
                    self.config.table.split(".")[-1],  # table
                    datetime.now(timezone.utc) - timedelta(milliseconds=duration_ms),
                    datetime.now(timezone.utc),
                    duration_ms,
                    rows_deleted,
                    cutoff,
                    self.config.retention_hours or (self.config.retention_days * 24),
                )
        except Exception as e:
            logger.warning("Failed to log cleanup audit: %s", e)


class ArchiveJob:
    """
    Signal archive job - moves old signals to archive, doesn't delete.

    For signals older than 90 days, we archive (move) rather than delete.
    """

    def __init__(
        self,
        name: str,
        source_table: str,
        archive_table: str,
        archive_after_days: int,
        db_pool: Any,
        batch_size: int = 1000,
    ):
        self.name = name
        self.source_table = source_table
        self.archive_table = archive_table
        self.archive_after_days = archive_after_days
        self._pool = db_pool
        self.batch_size = batch_size

    async def run(self, dry_run: bool = False) -> CleanupResult:
        """
        Run the archive job.

        Moves signals from source_table to archive_table.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=self.archive_after_days)
        start_time = datetime.now(timezone.utc)

        logger.info(
            "Archive job '%s' starting: %s -> %s, cutoff=%s",
            self.name,
            self.source_table,
            self.archive_table,
            cutoff.isoformat(),
        )

        try:
            # Count rows to archive
            count_query = f"""
                SELECT COUNT(*) FROM {self.source_table}
                WHERE generated_at < $1
            """
            async with self._pool.acquire() as conn:
                total_count = await conn.fetchval(count_query, cutoff)

            if dry_run:
                duration_ms = int(
                    (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
                )
                return CleanupResult(
                    job_name=self.name,
                    table=self.source_table,
                    status="DRY_RUN",
                    rows_affected=total_count,
                    duration_ms=duration_ms,
                    cutoff_timestamp=cutoff,
                    dry_run=True,
                )

            # Archive in batches (INSERT ... SELECT, then DELETE)
            archived = 0

            while archived < total_count:
                async with self._pool.acquire() as conn:
                    async with conn.transaction():
                        # Insert into archive
                        insert_result = await conn.execute(
                            f"""
                            INSERT INTO {self.archive_table}
                            SELECT * FROM {self.source_table}
                            WHERE generated_at < $1
                            AND signal_id NOT IN (
                                SELECT signal_id FROM {self.archive_table}
                            )
                            LIMIT {self.batch_size}
                            """,
                            cutoff,
                        )

                        # Delete from source
                        delete_result = await conn.execute(
                            f"""
                            DELETE FROM {self.source_table}
                            WHERE signal_id IN (
                                SELECT signal_id FROM {self.archive_table}
                                WHERE generated_at < $1
                            )
                            AND generated_at < $1
                            LIMIT {self.batch_size}
                            """,
                            cutoff,
                        )

                        batch_archived = int(delete_result.split()[-1])
                        archived += batch_archived

                        if batch_archived < self.batch_size:
                            break

                await asyncio.sleep(0.1)

            duration_ms = int(
                (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            )

            logger.info(
                "Archive job '%s' completed: archived %d rows in %dms",
                self.name,
                archived,
                duration_ms,
            )

            return CleanupResult(
                job_name=self.name,
                table=self.source_table,
                status="SUCCESS",
                rows_affected=archived,
                duration_ms=duration_ms,
                cutoff_timestamp=cutoff,
                dry_run=False,
            )

        except Exception as e:
            duration_ms = int(
                (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            )
            logger.error("Archive job '%s' failed: %s", self.name, e)

            return CleanupResult(
                job_name=self.name,
                table=self.source_table,
                status="FAILED",
                rows_affected=0,
                duration_ms=duration_ms,
                cutoff_timestamp=cutoff,
                dry_run=dry_run,
                error_message=str(e),
            )


# ═══════════════════════════════════════════════════════════════════════════════
# Default cleanup job configurations
# ═══════════════════════════════════════════════════════════════════════════════

DEFAULT_CLEANUP_CONFIGS = {
    "raw_inputs": CleanupConfig(
        table="demo.raw_inputs",
        retention_hours=72,
        timestamp_column="received_at",
        description="Raw API inputs (72-hour retention)",
    ),
    "ingestion_logs": CleanupConfig(
        table="demo.ingestion_logs",
        retention_days=30,
        timestamp_column="created_at",
        description="Ingestion pipeline logs (30-day retention)",
    ),
    "api_logs": CleanupConfig(
        table="audit.api_access_log",
        retention_days=90,
        timestamp_column="requested_at",
        description="API access audit logs (90-day retention)",
    ),
}


# ═══════════════════════════════════════════════════════════════════════════════
# CLI Entry Point
# ═══════════════════════════════════════════════════════════════════════════════


async def run_cleanup_job(
    job_name: str,
    dry_run: bool = False,
    dsn: Optional[str] = None,
) -> CleanupResult:
    """Run a specific cleanup job."""
    try:
        import asyncpg
    except ImportError:
        raise ImportError("asyncpg required: pip install asyncpg")

    dsn = dsn or os.environ.get("DATABASE_URL")
    if not dsn:
        raise ValueError("DATABASE_URL not set")

    if job_name not in DEFAULT_CLEANUP_CONFIGS:
        raise ValueError(f"Unknown job: {job_name}. Available: {list(DEFAULT_CLEANUP_CONFIGS.keys())}")

    config = DEFAULT_CLEANUP_CONFIGS[job_name]
    pool = await asyncpg.create_pool(dsn, min_size=1, max_size=2)

    try:
        job = CleanupJob(job_name, config, pool)
        return await job.run(dry_run=dry_run)
    finally:
        await pool.close()


async def run_all_cleanup_jobs(dry_run: bool = False, dsn: Optional[str] = None) -> list[CleanupResult]:
    """Run all cleanup jobs."""
    results = []
    for job_name in DEFAULT_CLEANUP_CONFIGS:
        result = await run_cleanup_job(job_name, dry_run=dry_run, dsn=dsn)
        results.append(result)
    return results


def main() -> None:
    """CLI entry point."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    parser = argparse.ArgumentParser(description="Database cleanup job")
    parser.add_argument(
        "--job",
        choices=list(DEFAULT_CLEANUP_CONFIGS.keys()),
        help="Specific job to run",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run all cleanup jobs",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Count rows without deleting",
    )
    parser.add_argument(
        "--dsn",
        default=None,
        help="Database connection string (default: DATABASE_URL env)",
    )
    args = parser.parse_args()

    if not args.job and not args.all:
        parser.error("Must specify --job or --all")

    if args.all:
        results = asyncio.run(run_all_cleanup_jobs(dry_run=args.dry_run, dsn=args.dsn))
        for result in results:
            status_emoji = "✓" if result.status == "SUCCESS" else "✗" if result.status == "FAILED" else "○"
            print(f"{status_emoji} {result.job_name}: {result.rows_affected} rows ({result.status})")
    else:
        result = asyncio.run(run_cleanup_job(args.job, dry_run=args.dry_run, dsn=args.dsn))
        print(f"Job: {result.job_name}")
        print(f"Table: {result.table}")
        print(f"Status: {result.status}")
        print(f"Rows affected: {result.rows_affected}")
        print(f"Duration: {result.duration_ms}ms")
        print(f"Cutoff: {result.cutoff_timestamp}")


if __name__ == "__main__":
    main()
