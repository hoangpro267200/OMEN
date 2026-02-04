"""
Job Scheduler for OMEN Background Tasks.

Manages scheduled execution of:
- Cleanup jobs (data retention)
- Archive jobs (signal archiving)
- Lifecycle jobs (ledger management)

Usage:
    # Start scheduler
    python -m omen.jobs.scheduler

    # Or programmatically
    scheduler = JobScheduler(db_pool)
    await scheduler.start()
"""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional

from omen.jobs.cleanup_job import (
    CleanupJob,
    ArchiveJob,
    CleanupConfig,
    CleanupResult,
    DEFAULT_CLEANUP_CONFIGS,
)
from pathlib import Path

logger = logging.getLogger(__name__)


class LifecycleJobWrapper:
    """
    Wrapper for lifecycle job to integrate with JobScheduler.
    
    Runs ledger lifecycle tasks (partition sealing, tiering, archiving).
    """

    def __init__(self, db_pool: Any):
        self._pool = db_pool

    async def run(self, dry_run: bool = False) -> CleanupResult:
        """Run lifecycle tasks."""
        from datetime import datetime, timezone
        import time
        
        start_time = time.time()
        
        try:
            from omen.config import get_config
            from omen.infrastructure.ledger.lifecycle import LedgerLifecycleManager
            
            config = get_config()
            base_path = Path(config.ledger_base_path)
            
            if not base_path.exists():
                return CleanupResult(
                    job_name="lifecycle_ledger",
                    status="SKIPPED",
                    rows_affected=0,
                    duration_ms=int((time.time() - start_time) * 1000),
                    started_at=datetime.now(timezone.utc),
                    error_message="Ledger base path does not exist",
                )
            
            manager = LedgerLifecycleManager(
                base_path,
                config.retention,
                archive_path=config.retention.archive_path,
            )
            
            if dry_run:
                stats = manager.get_storage_stats()
                return CleanupResult(
                    job_name="lifecycle_ledger",
                    status="DRY_RUN",
                    rows_affected=stats.total_records,
                    duration_ms=int((time.time() - start_time) * 1000),
                    started_at=datetime.now(timezone.utc),
                )
            
            results = await manager.run_lifecycle_tasks()
            
            # Count affected partitions
            affected = sum(
                len(results.get(key, []))
                for key in ["sealed", "tiered", "archived", "deleted"]
            )
            
            return CleanupResult(
                job_name="lifecycle_ledger",
                status="SUCCESS",
                rows_affected=affected,
                duration_ms=int((time.time() - start_time) * 1000),
                started_at=datetime.now(timezone.utc),
            )
            
        except ImportError as e:
            return CleanupResult(
                job_name="lifecycle_ledger",
                status="SKIPPED",
                rows_affected=0,
                duration_ms=int((time.time() - start_time) * 1000),
                started_at=datetime.now(timezone.utc),
                error_message=f"Lifecycle module not available: {e}",
            )
        except Exception as e:
            logger.error("Lifecycle job error: %s", e)
            return CleanupResult(
                job_name="lifecycle_ledger",
                status="ERROR",
                rows_affected=0,
                duration_ms=int((time.time() - start_time) * 1000),
                started_at=datetime.now(timezone.utc),
                error_message=str(e),
            )


class JobScheduler:
    """
    Async job scheduler for background tasks.

    Features:
    - Cron-like scheduling
    - Graceful shutdown
    - Manual job triggers
    - Job status tracking
    """

    def __init__(self, db_pool: Any):
        """
        Initialize job scheduler.

        Args:
            db_pool: asyncpg connection pool
        """
        self._pool = db_pool
        self._running = False
        self._tasks: Dict[str, asyncio.Task] = {}
        self._jobs: Dict[str, Dict] = {}
        self._last_run: Dict[str, datetime] = {}
        self._next_run: Dict[str, datetime] = {}

        # Initialize default jobs
        self._setup_default_jobs()

    def _setup_default_jobs(self) -> None:
        """Setup default cleanup jobs."""
        # Cleanup: raw_inputs (every 6 hours)
        self._jobs["cleanup_raw_inputs"] = {
            "job": lambda: CleanupJob(
                "cleanup_raw_inputs",
                DEFAULT_CLEANUP_CONFIGS["raw_inputs"],
                self._pool,
            ),
            "interval_hours": 6,
            "description": "Clean up raw inputs older than 72 hours",
        }

        # Cleanup: ingestion_logs (daily at 3 AM)
        self._jobs["cleanup_ingestion_logs"] = {
            "job": lambda: CleanupJob(
                "cleanup_ingestion_logs",
                DEFAULT_CLEANUP_CONFIGS["ingestion_logs"],
                self._pool,
            ),
            "interval_hours": 24,
            "run_hour": 3,
            "description": "Clean up ingestion logs older than 30 days",
        }

        # Cleanup: api_logs (weekly on Sunday at 4 AM)
        self._jobs["cleanup_api_logs"] = {
            "job": lambda: CleanupJob(
                "cleanup_api_logs",
                DEFAULT_CLEANUP_CONFIGS["api_logs"],
                self._pool,
            ),
            "interval_hours": 168,  # Weekly
            "run_hour": 4,
            "run_weekday": 6,  # Sunday
            "description": "Clean up API access logs older than 90 days",
        }

        # Lifecycle: ledger management (daily at 2 AM)
        self._jobs["lifecycle_ledger"] = {
            "job": lambda: LifecycleJobWrapper(self._pool),
            "interval_hours": 24,
            "run_hour": 2,
            "description": "Ledger lifecycle management (partition sealing, archiving)",
        }

    async def start(self) -> None:
        """Start the scheduler."""
        if self._running:
            logger.warning("Scheduler already running")
            return

        self._running = True
        logger.info("Starting job scheduler with %d jobs", len(self._jobs))

        # Start scheduler loop
        self._tasks["_scheduler"] = asyncio.create_task(self._scheduler_loop())

        logger.info("Job scheduler started")

    async def stop(self) -> None:
        """Stop the scheduler gracefully."""
        if not self._running:
            return

        logger.info("Stopping job scheduler...")
        self._running = False

        # Cancel all tasks
        for name, task in self._tasks.items():
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        self._tasks.clear()
        logger.info("Job scheduler stopped")

    async def run_job_now(self, job_name: str, dry_run: bool = False) -> CleanupResult:
        """
        Manually trigger a job.

        Args:
            job_name: Name of the job to run
            dry_run: If True, only count without modifying

        Returns:
            CleanupResult from the job
        """
        if job_name not in self._jobs:
            raise ValueError(f"Unknown job: {job_name}")

        logger.info("Manual trigger: %s (dry_run=%s)", job_name, dry_run)

        job_config = self._jobs[job_name]
        job = job_config["job"]()
        result = await job.run(dry_run=dry_run)

        self._last_run[job_name] = datetime.now(timezone.utc)

        return result

    async def _scheduler_loop(self) -> None:
        """Main scheduler loop."""
        while self._running:
            try:
                now = datetime.now(timezone.utc)

                for job_name, job_config in self._jobs.items():
                    if self._should_run_job(job_name, job_config, now):
                        # Run job in background
                        asyncio.create_task(self._run_job_safe(job_name, job_config))
                        self._last_run[job_name] = now

                # Check every minute
                await asyncio.sleep(60)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Scheduler loop error: %s", e)
                await asyncio.sleep(60)

    def _should_run_job(
        self,
        job_name: str,
        job_config: Dict,
        now: datetime,
    ) -> bool:
        """Check if a job should run now."""
        last_run = self._last_run.get(job_name)
        interval_hours = job_config.get("interval_hours", 24)

        # Never run before
        if last_run is None:
            # Check if we should wait for specific hour
            run_hour = job_config.get("run_hour")
            if run_hour is not None and now.hour != run_hour:
                return False

            run_weekday = job_config.get("run_weekday")
            if run_weekday is not None and now.weekday() != run_weekday:
                return False

            return True

        # Check interval
        hours_since_last = (now - last_run).total_seconds() / 3600
        if hours_since_last < interval_hours:
            return False

        # Check hour constraint
        run_hour = job_config.get("run_hour")
        if run_hour is not None and now.hour != run_hour:
            return False

        # Check weekday constraint
        run_weekday = job_config.get("run_weekday")
        if run_weekday is not None and now.weekday() != run_weekday:
            return False

        return True

    async def _run_job_safe(self, job_name: str, job_config: Dict) -> None:
        """Run a job with error handling."""
        try:
            logger.info("Running scheduled job: %s", job_name)
            job = job_config["job"]()
            result = await job.run(dry_run=False)

            if result.status == "SUCCESS":
                logger.info(
                    "Job %s completed: %d rows in %dms",
                    job_name,
                    result.rows_affected,
                    result.duration_ms,
                )
            else:
                logger.error(
                    "Job %s failed: %s",
                    job_name,
                    result.error_message,
                )

        except Exception as e:
            logger.error("Job %s error: %s", job_name, e)

    def get_status(self) -> Dict:
        """Get scheduler status."""
        now = datetime.now(timezone.utc)

        job_statuses = {}
        for job_name, job_config in self._jobs.items():
            last_run = self._last_run.get(job_name)
            interval_hours = job_config.get("interval_hours", 24)

            if last_run:
                next_run = last_run.replace(
                    hour=(last_run.hour + interval_hours) % 24
                )
                hours_until_next = max(
                    0, (next_run - now).total_seconds() / 3600
                )
            else:
                hours_until_next = 0

            job_statuses[job_name] = {
                "description": job_config.get("description", ""),
                "interval_hours": interval_hours,
                "last_run": last_run.isoformat() if last_run else None,
                "hours_until_next": round(hours_until_next, 1),
            }

        return {
            "running": self._running,
            "jobs": job_statuses,
            "checked_at": now.isoformat(),
        }

    def list_jobs(self) -> list[str]:
        """List available job names."""
        return list(self._jobs.keys())


# ═══════════════════════════════════════════════════════════════════════════════
# CLI Entry Point
# ═══════════════════════════════════════════════════════════════════════════════


async def main_async() -> None:
    """Async main function."""
    try:
        import asyncpg
    except ImportError:
        raise ImportError("asyncpg required: pip install asyncpg")

    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        raise ValueError("DATABASE_URL not set")

    pool = await asyncpg.create_pool(dsn, min_size=2, max_size=5)

    scheduler = JobScheduler(pool)
    await scheduler.start()

    try:
        # Keep running until interrupted
        while True:
            await asyncio.sleep(3600)
    except asyncio.CancelledError:
        pass
    finally:
        await scheduler.stop()
        await pool.close()


def main() -> None:
    """CLI entry point."""
    import argparse

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    parser = argparse.ArgumentParser(description="OMEN Job Scheduler")
    parser.add_argument(
        "--list",
        action="store_true",
        help="List available jobs",
    )
    args = parser.parse_args()

    if args.list:
        print("Available cleanup jobs:")
        for name, config in DEFAULT_CLEANUP_CONFIGS.items():
            print(f"  - {name}: {config.description} ({config.retention_description})")
        return

    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        print("\nShutdown requested...")


if __name__ == "__main__":
    main()
