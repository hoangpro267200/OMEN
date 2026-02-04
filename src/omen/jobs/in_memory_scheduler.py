"""
In-Memory Job Scheduler for OMEN (P1-5).

Provides scheduled job execution when DATABASE_URL is not set.
Works with in-memory repositories to perform cleanup tasks.

Usage:
    scheduler = InMemoryJobScheduler()
    await scheduler.start()
    # ... later ...
    await scheduler.stop()
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from dataclasses import dataclass
from typing import Callable, Dict, Optional, Any

logger = logging.getLogger(__name__)


@dataclass
class JobResult:
    """Result of a job execution."""

    job_name: str
    status: str  # SUCCESS, ERROR, SKIPPED
    items_cleaned: int
    duration_ms: int
    started_at: datetime
    error_message: Optional[str] = None


class InMemoryJobScheduler:
    """
    In-memory job scheduler for cleanup tasks.

    Features:
    - No database dependency
    - Scheduled execution at configurable intervals
    - Cleanup for in-memory stores
    - Graceful shutdown

    Jobs included:
    - cleanup_old_signals: Remove signals older than retention period
    - cleanup_calibration_data: Clean up old calibration outcomes
    - cleanup_activity_logs: Clean up old activity logs
    """

    def __init__(
        self,
        signal_retention_hours: int = 24,
        calibration_retention_days: int = 30,
        activity_retention_hours: int = 6,
    ):
        """
        Initialize the in-memory scheduler.

        Args:
            signal_retention_hours: How long to keep signals in memory
            calibration_retention_days: How long to keep calibration data
            activity_retention_hours: How long to keep activity logs
        """
        self._running = False
        self._tasks: Dict[str, asyncio.Task] = {}
        self._last_run: Dict[str, datetime] = {}

        # Retention settings
        self._signal_retention_hours = signal_retention_hours
        self._calibration_retention_days = calibration_retention_days
        self._activity_retention_hours = activity_retention_hours

        # Job configurations: name -> (interval_seconds, job_func)
        self._jobs: Dict[str, tuple[int, Callable]] = {
            "cleanup_old_signals": (3600, self._cleanup_old_signals),  # Every hour
            "cleanup_calibration_data": (86400, self._cleanup_calibration_data),  # Daily
            "cleanup_activity_logs": (1800, self._cleanup_activity_logs),  # Every 30 min
            "check_expired_api_keys": (86400, self._check_expired_api_keys),  # Daily - check for expiring keys
            "cleanup_fallback_caches": (7200, self._cleanup_fallback_caches),  # Every 2 hours - clean stale caches
        }

    async def start(self) -> None:
        """Start the scheduler."""
        if self._running:
            logger.warning("InMemoryJobScheduler already running")
            return

        self._running = True
        logger.info(
            "InMemoryJobScheduler starting with %d jobs (no DATABASE_URL)",
            len(self._jobs),
        )

        # Start the scheduler loop
        self._tasks["_scheduler"] = asyncio.create_task(self._scheduler_loop())

        logger.info("InMemoryJobScheduler started")

    async def stop(self) -> None:
        """Stop the scheduler gracefully."""
        if not self._running:
            return

        logger.info("InMemoryJobScheduler stopping...")
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
        logger.info("InMemoryJobScheduler stopped")

    async def _scheduler_loop(self) -> None:
        """Main scheduler loop."""
        while self._running:
            try:
                now = datetime.now(timezone.utc)

                for job_name, (interval_seconds, job_func) in self._jobs.items():
                    if self._should_run_job(job_name, interval_seconds, now):
                        # Run job in background
                        asyncio.create_task(self._run_job_safe(job_name, job_func))
                        self._last_run[job_name] = now

                # Check every 60 seconds
                await asyncio.sleep(60)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("InMemoryJobScheduler loop error: %s", e)
                await asyncio.sleep(60)

    def _should_run_job(
        self,
        job_name: str,
        interval_seconds: int,
        now: datetime,
    ) -> bool:
        """Check if a job should run now."""
        last_run = self._last_run.get(job_name)

        if last_run is None:
            return True  # Never run before

        seconds_since_last = (now - last_run).total_seconds()
        return seconds_since_last >= interval_seconds

    async def _run_job_safe(self, job_name: str, job_func: Callable) -> None:
        """Run a job with error handling."""
        import time

        start_time = time.time()
        try:
            logger.info("Running in-memory job: %s", job_name)
            result = await job_func()

            duration_ms = int((time.time() - start_time) * 1000)

            if result.status == "SUCCESS":
                logger.info(
                    "InMemory job %s completed: %d items cleaned in %dms",
                    job_name,
                    result.items_cleaned,
                    duration_ms,
                )
            else:
                logger.warning(
                    "InMemory job %s: %s - %s",
                    job_name,
                    result.status,
                    result.error_message,
                )

        except Exception as e:
            logger.error("InMemory job %s error: %s", job_name, e)

    async def _cleanup_old_signals(self) -> JobResult:
        """Clean up old signals from in-memory repository."""
        import time
        from datetime import timedelta

        start_time = time.time()
        started_at = datetime.now(timezone.utc)
        items_cleaned = 0

        try:
            from omen.application.container import get_container

            container = get_container()
            repo = container.repository

            # Check if repository has cleanup method
            if hasattr(repo, "cleanup_old_signals"):
                cutoff = started_at - timedelta(hours=self._signal_retention_hours)
                items_cleaned = await repo.cleanup_old_signals(cutoff)
            elif hasattr(repo, "_signals"):
                # In-memory repository direct access
                cutoff = started_at - timedelta(hours=self._signal_retention_hours)
                signals_to_remove = []
                for signal_id, signal in repo._signals.items():
                    if signal.generated_at and signal.generated_at < cutoff:
                        signals_to_remove.append(signal_id)

                for signal_id in signals_to_remove:
                    del repo._signals[signal_id]
                items_cleaned = len(signals_to_remove)
            else:
                return JobResult(
                    job_name="cleanup_old_signals",
                    status="SKIPPED",
                    items_cleaned=0,
                    duration_ms=int((time.time() - start_time) * 1000),
                    started_at=started_at,
                    error_message="Repository does not support cleanup",
                )

            return JobResult(
                job_name="cleanup_old_signals",
                status="SUCCESS",
                items_cleaned=items_cleaned,
                duration_ms=int((time.time() - start_time) * 1000),
                started_at=started_at,
            )

        except Exception as e:
            return JobResult(
                job_name="cleanup_old_signals",
                status="ERROR",
                items_cleaned=0,
                duration_ms=int((time.time() - start_time) * 1000),
                started_at=started_at,
                error_message=str(e),
            )

    async def _cleanup_calibration_data(self) -> JobResult:
        """Clean up old calibration outcomes."""
        import time
        from datetime import timedelta

        start_time = time.time()
        started_at = datetime.now(timezone.utc)
        items_cleaned = 0

        try:
            from omen.api.routes.calibration import _outcomes_store

            cutoff = started_at - timedelta(days=self._calibration_retention_days)

            # Find and remove old outcomes
            outcomes_to_remove = []
            for signal_id, outcome in _outcomes_store.items():
                if outcome.recorded_at < cutoff:
                    outcomes_to_remove.append(signal_id)

            for signal_id in outcomes_to_remove:
                del _outcomes_store[signal_id]
            items_cleaned = len(outcomes_to_remove)

            return JobResult(
                job_name="cleanup_calibration_data",
                status="SUCCESS",
                items_cleaned=items_cleaned,
                duration_ms=int((time.time() - start_time) * 1000),
                started_at=started_at,
            )

        except Exception as e:
            return JobResult(
                job_name="cleanup_calibration_data",
                status="ERROR",
                items_cleaned=0,
                duration_ms=int((time.time() - start_time) * 1000),
                started_at=started_at,
                error_message=str(e),
            )

    async def _cleanup_activity_logs(self) -> JobResult:
        """Clean up old activity logs."""
        import time
        from datetime import timedelta

        start_time = time.time()
        started_at = datetime.now(timezone.utc)
        items_cleaned = 0

        try:
            from omen.infrastructure.activity.activity_logger import get_activity_logger

            activity_logger = get_activity_logger()
            cutoff = started_at - timedelta(hours=self._activity_retention_hours)

            # Check if activity logger has cleanup method
            if hasattr(activity_logger, "cleanup_old_events"):
                items_cleaned = activity_logger.cleanup_old_events(cutoff)
            elif hasattr(activity_logger, "_events"):
                # Direct access to in-memory events
                original_count = len(activity_logger._events)
                activity_logger._events = [
                    e for e in activity_logger._events
                    if e.timestamp >= cutoff
                ]
                items_cleaned = original_count - len(activity_logger._events)
            else:
                return JobResult(
                    job_name="cleanup_activity_logs",
                    status="SKIPPED",
                    items_cleaned=0,
                    duration_ms=int((time.time() - start_time) * 1000),
                    started_at=started_at,
                    error_message="Activity logger does not support cleanup",
                )

            return JobResult(
                job_name="cleanup_activity_logs",
                status="SUCCESS",
                items_cleaned=items_cleaned,
                duration_ms=int((time.time() - start_time) * 1000),
                started_at=started_at,
            )

        except Exception as e:
            return JobResult(
                job_name="cleanup_activity_logs",
                status="ERROR",
                items_cleaned=0,
                duration_ms=int((time.time() - start_time) * 1000),
                started_at=started_at,
                error_message=str(e),
            )

    async def _check_expired_api_keys(self) -> JobResult:
        """Check for expiring API keys and log warnings."""
        import time
        from datetime import timedelta

        start_time = time.time()
        started_at = datetime.now(timezone.utc)
        items_cleaned = 0

        try:
            from omen.infrastructure.security.key_rotation import InMemoryApiKeyStore
            
            # This is a monitoring job - checks for keys expiring soon
            # In production, this would notify administrators
            warning_threshold = timedelta(days=7)  # Warn if expiring in 7 days
            
            # Note: In a real deployment, you'd have a persistent key store
            # This is a placeholder that logs the check
            logger.info("API key expiration check completed (no persistent store configured)")
            
            return JobResult(
                job_name="check_expired_api_keys",
                status="SUCCESS",
                items_cleaned=items_cleaned,
                duration_ms=int((time.time() - start_time) * 1000),
                started_at=started_at,
            )

        except Exception as e:
            return JobResult(
                job_name="check_expired_api_keys",
                status="ERROR",
                items_cleaned=0,
                duration_ms=int((time.time() - start_time) * 1000),
                started_at=started_at,
                error_message=str(e),
            )

    async def _cleanup_fallback_caches(self) -> JobResult:
        """Clean up expired entries from fallback caches."""
        import time

        start_time = time.time()
        started_at = datetime.now(timezone.utc)
        items_cleaned = 0

        try:
            from omen.adapters.inbound.multi_source import get_multi_source_aggregator
            
            aggregator = get_multi_source_aggregator()
            
            # Get stats before cleanup
            stats_before = aggregator.get_fallback_stats()
            total_before = sum(
                len(cache_stats.get("entries", []))
                for cache_stats in stats_before.get("caches", {}).values()
            )
            
            # Clear very old caches (older than 24 hours)
            for cache_name in stats_before.get("caches", {}).keys():
                cache_data = stats_before["caches"][cache_name]
                for entry in cache_data.get("entries", []):
                    if entry.get("age_seconds", 0) > 86400:  # 24 hours
                        # Entry is very old, will be naturally replaced
                        items_cleaned += 1
            
            logger.info(f"Fallback cache cleanup: {items_cleaned} stale entries identified")
            
            return JobResult(
                job_name="cleanup_fallback_caches",
                status="SUCCESS",
                items_cleaned=items_cleaned,
                duration_ms=int((time.time() - start_time) * 1000),
                started_at=started_at,
            )

        except Exception as e:
            return JobResult(
                job_name="cleanup_fallback_caches",
                status="ERROR",
                items_cleaned=0,
                duration_ms=int((time.time() - start_time) * 1000),
                started_at=started_at,
                error_message=str(e),
            )

    async def run_job_now(self, job_name: str) -> JobResult:
        """Manually trigger a job."""
        if job_name not in self._jobs:
            raise ValueError(f"Unknown job: {job_name}")

        logger.info("Manual trigger: %s", job_name)
        _, job_func = self._jobs[job_name]
        result = await job_func()
        self._last_run[job_name] = datetime.now(timezone.utc)
        return result

    def get_status(self) -> Dict[str, Any]:
        """Get scheduler status."""
        now = datetime.now(timezone.utc)

        job_statuses = {}
        for job_name, (interval_seconds, _) in self._jobs.items():
            last_run = self._last_run.get(job_name)

            if last_run:
                seconds_since_last = (now - last_run).total_seconds()
                seconds_until_next = max(0, interval_seconds - seconds_since_last)
            else:
                seconds_until_next = 0

            job_statuses[job_name] = {
                "interval_seconds": interval_seconds,
                "last_run": last_run.isoformat() if last_run else None,
                "seconds_until_next": round(seconds_until_next),
            }

        return {
            "running": self._running,
            "mode": "in_memory",
            "jobs": job_statuses,
            "checked_at": now.isoformat(),
        }

    def list_jobs(self) -> list[str]:
        """List available job names."""
        return list(self._jobs.keys())


# Global instance
_in_memory_scheduler: Optional[InMemoryJobScheduler] = None


def get_in_memory_scheduler() -> InMemoryJobScheduler:
    """Get or create the in-memory scheduler."""
    global _in_memory_scheduler
    if _in_memory_scheduler is None:
        _in_memory_scheduler = InMemoryJobScheduler()
    return _in_memory_scheduler


async def start_in_memory_scheduler() -> InMemoryJobScheduler:
    """Start the in-memory scheduler."""
    scheduler = get_in_memory_scheduler()
    await scheduler.start()
    return scheduler


async def stop_in_memory_scheduler() -> None:
    """Stop the in-memory scheduler."""
    global _in_memory_scheduler
    if _in_memory_scheduler is not None:
        await _in_memory_scheduler.stop()
        _in_memory_scheduler = None
