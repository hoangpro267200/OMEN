"""
Reconcile Job v2 — Highwater Detection

Verifies RiskCast processed all signals from OMEN ledger.
Detects and handles late arrivals via highwater tracking.

Key improvements:
- Tracks highwater per partition
- Re-reconciles when late arrivals detected
- Separate handling for main vs late partitions
- Persistent reconcile state
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from enum import Enum
from typing import Optional

import httpx

from riskcast.infrastructure.reconcile_state import (
    ReconcileState,
    ReconcileStateStore,
    get_reconcile_store,
)
from riskcast.infrastructure.signal_store import SignalStore, get_store

logger = logging.getLogger(__name__)


class ReconcileStatus(str, Enum):
    COMPLETED = "COMPLETED"
    SKIPPED = "SKIPPED"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"


@dataclass
class ReconcileResult:
    """Result of reconciling a single partition."""

    status: ReconcileStatus
    partition: str
    reason: Optional[str] = None
    ledger_count: int = 0
    processed_count: int = 0
    missing_count: int = 0
    replayed_count: int = 0
    replayed_ids: list[str] = field(default_factory=list)
    failed_ids: list[str] = field(default_factory=list)
    extra_ids: list[str] = field(default_factory=list)
    duration_ms: int = 0
    highwater: int = 0
    manifest_revision: int = 0
    is_rereconcile: bool = False
    error: Optional[str] = None


class LedgerClient:
    """
    Client to read from OMEN ledger.

    Provides:
    - Partition listing with seal status
    - Signal reading with validation
    - Highwater mark retrieval
    """

    def __init__(self, ledger_path: str):
        self.ledger_path = ledger_path
        from omen.infrastructure.ledger import LedgerReader

        self.reader = LedgerReader(ledger_path)

    def is_partition_sealed(self, partition_date: str) -> bool:
        """Check if partition is sealed."""
        return self.reader.is_partition_sealed(partition_date)

    def get_partition_info(self, partition_date: str):
        """Get partition metadata."""
        partitions = self.reader.list_partitions()
        for p in partitions:
            if p.partition_date == partition_date:
                return p
        return None

    def get_highwater(self, partition_date: str) -> tuple[int, int]:
        """
        Get highwater mark for partition.

        Returns:
            (highwater_sequence, manifest_revision)
        """
        return self.reader.get_partition_highwater(partition_date)

    def list_signal_ids(self, partition_date: str) -> list[str]:
        """List all signal_ids in partition."""
        return self.reader.list_signal_ids(partition_date)

    def get_signal(self, partition_date: str, signal_id: str):
        """Get specific signal for replay."""
        return self.reader.get_signal(partition_date, signal_id)

    def list_partitions_for_reconcile(self, since_days: int = 7) -> list[dict]:
        """
        List partitions that may need reconcile.

        Returns both main and late partitions.
        Includes seal status.
        """
        partitions = []
        cutoff = date.today() - timedelta(days=since_days)

        for info in self.reader.list_partitions():
            try:
                base_date_str = info.partition_date.replace("-late", "")
                partition_date_obj = date.fromisoformat(base_date_str)

                if partition_date_obj < cutoff:
                    continue

                highwater, revision = self.reader.get_partition_highwater(info.partition_date)
                partitions.append(
                    {
                        "partition_date": info.partition_date,
                        "base_date": base_date_str,
                        "is_late": info.is_late,
                        "is_sealed": info.is_sealed,
                        "total_records": info.total_records,
                        "highwater": highwater,
                        "manifest_revision": revision,
                    }
                )
            except ValueError:
                continue

        return partitions


class ReconcileJob:
    """
    Enhanced reconcile job with highwater detection.

    Reconcile strategy:
    1. For each partition in window (last N days):
       a. Get current highwater from ledger
       b. Check if reconcile needed (never done, highwater changed, failed)
       c. If needed: compare ledger vs processed, replay missing
       d. Save state with new highwater

    2. Main partitions: reconcile only if sealed
    3. Late partitions: reconcile even if not sealed (within grace window)
    4. Re-reconcile: triggered by highwater increase
    """

    def __init__(
        self,
        ledger_client: LedgerClient,
        signal_store: SignalStore,
        reconcile_store: ReconcileStateStore,
        riskcast_ingest_url: str,
        api_key: str,
        max_replay_batch: int = 100,
    ):
        self.ledger = ledger_client
        self.signal_store = signal_store
        self.reconcile_store = reconcile_store
        self.ingest_url = riskcast_ingest_url
        self.api_key = api_key
        self.max_replay_batch = max_replay_batch

    async def reconcile_partition(self, partition_date: str) -> ReconcileResult:
        """
        Reconcile a single partition.

        Handles both main and late partitions.
        Tracks highwater for re-reconcile detection.
        """
        start_time = time.monotonic()

        logger.info("Reconciling partition: %s", partition_date)

        info = self.ledger.get_partition_info(partition_date)
        if info is None:
            return ReconcileResult(
                status=ReconcileStatus.SKIPPED,
                partition=partition_date,
                reason="partition_not_found",
            )

        is_late = "-late" in partition_date

        if not is_late and not info.is_sealed:
            return ReconcileResult(
                status=ReconcileStatus.SKIPPED,
                partition=partition_date,
                reason="main_partition_not_sealed",
            )

        current_highwater, current_revision = self.ledger.get_highwater(partition_date)

        needs_reconcile, reason = await self.reconcile_store.needs_reconcile(
            partition_date,
            current_highwater,
            current_revision,
        )

        if not needs_reconcile:
            logger.info("Partition %s up to date, skipping", partition_date)
            return ReconcileResult(
                status=ReconcileStatus.SKIPPED,
                partition=partition_date,
                reason=reason,
                highwater=current_highwater,
                manifest_revision=current_revision,
            )

        is_rereconcile = "highwater_increased" in reason
        if is_rereconcile:
            logger.warning("Re-reconciling %s: %s", partition_date, reason)

        try:
            ledger_ids = set(self.ledger.list_signal_ids(partition_date))
        except Exception as e:
            logger.exception("Failed to read ledger for %s: %s", partition_date, e)
            return ReconcileResult(
                status=ReconcileStatus.FAILED,
                partition=partition_date,
                reason="ledger_read_error",
                error=str(e),
            )

        logger.info(
            "Ledger has %s signals for %s",
            len(ledger_ids),
            partition_date,
        )

        processed_ids = set(await self.signal_store.list_processed_ids(partition_date))

        if is_late:
            base_date = partition_date.replace("-late", "")
            main_processed = set(await self.signal_store.list_processed_ids(base_date))
            processed_ids.update(main_processed)

        logger.info(
            "Processed %s signals for %s",
            len(processed_ids),
            partition_date,
        )

        missing_ids = ledger_ids - processed_ids
        extra_ids = list(processed_ids - ledger_ids)
        if extra_ids:
            logger.error(
                "CRITICAL: Extra signals not in ledger for %s: %s...",
                partition_date,
                extra_ids[:10],
            )

        replayed_ids: list[str] = []
        failed_ids: list[str] = []

        if missing_ids:
            logger.warning(
                "Found %s missing signals for %s",
                len(missing_ids),
                partition_date,
            )

            for signal_id in list(missing_ids)[: self.max_replay_batch]:
                try:
                    signal = self.ledger.get_signal(partition_date, signal_id)
                    if signal:
                        await self._replay_signal(signal, partition_date)
                        replayed_ids.append(signal_id)
                        logger.debug("Replayed: %s", signal_id)
                except Exception as e:
                    logger.error("Failed to replay %s: %s", signal_id, e)
                    failed_ids.append(signal_id)

        if failed_ids:
            status = ReconcileStatus.PARTIAL
        elif len(missing_ids) > self.max_replay_batch:
            status = ReconcileStatus.PARTIAL
            logger.warning(
                "Capped replay at %s, %s remaining",
                self.max_replay_batch,
                len(missing_ids) - self.max_replay_batch,
            )
        else:
            status = ReconcileStatus.COMPLETED

        duration_ms = int((time.monotonic() - start_time) * 1000)

        await self.reconcile_store.save_state(
            partition_date=partition_date,
            ledger_highwater=current_highwater,
            manifest_revision=current_revision,
            ledger_record_count=len(ledger_ids),
            processed_count=len(processed_ids),
            missing_count=len(missing_ids),
            replayed_count=len(replayed_ids),
            status=status.value,
            duration_ms=duration_ms,
        )

        return ReconcileResult(
            status=status,
            partition=partition_date,
            reason=reason,
            ledger_count=len(ledger_ids),
            processed_count=len(processed_ids),
            missing_count=len(missing_ids),
            replayed_count=len(replayed_ids),
            replayed_ids=replayed_ids,
            failed_ids=failed_ids,
            extra_ids=extra_ids,
            duration_ms=duration_ms,
            highwater=current_highwater,
            manifest_revision=current_revision,
            is_rereconcile=is_rereconcile,
        )

    async def _replay_signal(self, signal_event, partition_date: str) -> None:
        """
        Replay signal through ingest endpoint.

        Marks source as 'reconcile' for audit.
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            payload = signal_event.model_dump(mode="json")
            response = await client.post(
                self.ingest_url,
                json=payload,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "X-Idempotency-Key": signal_event.signal_id,
                    "X-Replay-Source": "reconcile",
                    "X-Replay-Partition": partition_date,
                },
            )

            if response.status_code == 409:
                logger.debug(
                    "Signal already processed during replay: %s",
                    signal_event.signal_id,
                )
                return

            response.raise_for_status()

    async def run(
        self,
        since_days: int = 7,
        include_late: bool = True,
    ) -> list[ReconcileResult]:
        """
        Run reconcile for all relevant partitions.

        Args:
            since_days: Reconcile partitions from last N days
            include_late: Include late partitions

        Returns:
            List of ReconcileResult for each partition
        """
        logger.info("Starting reconcile job (last %s days)", since_days)

        results: list[ReconcileResult] = []
        partitions = self.ledger.list_partitions_for_reconcile(since_days)

        partitions.sort(key=lambda p: (p["is_late"], p["partition_date"]))

        logger.info("Found %s partitions to check", len(partitions))

        for p in partitions:
            if p["is_late"] and not include_late:
                continue

            result = await self.reconcile_partition(p["partition_date"])
            results.append(result)

            if result.status == ReconcileStatus.COMPLETED:
                if result.missing_count > 0:
                    logger.info(
                        "✓ %s: replayed %s signals",
                        p["partition_date"],
                        result.replayed_count,
                    )
                else:
                    logger.debug("✓ %s: up to date", p["partition_date"])
            elif result.status == ReconcileStatus.PARTIAL:
                logger.warning(
                    "⚠ %s: partial - replayed %s, failed %s",
                    p["partition_date"],
                    result.replayed_count,
                    len(result.failed_ids),
                )
            elif result.status == ReconcileStatus.FAILED:
                logger.error(
                    "✗ %s: failed - %s",
                    p["partition_date"],
                    result.error,
                )

        completed = sum(1 for r in results if r.status == ReconcileStatus.COMPLETED)
        partial = sum(1 for r in results if r.status == ReconcileStatus.PARTIAL)
        failed = sum(1 for r in results if r.status == ReconcileStatus.FAILED)
        skipped = sum(1 for r in results if r.status == ReconcileStatus.SKIPPED)
        total_replayed = sum(r.replayed_count for r in results)
        total_missing = sum(r.missing_count for r in results)
        rereconciled = sum(1 for r in results if r.is_rereconcile)

        logger.info(
            "Reconcile complete: %s completed, %s partial, %s failed, %s skipped, "
            "%s missing, %s replayed, %s re-reconciled",
            completed,
            partial,
            failed,
            skipped,
            total_missing,
            total_replayed,
            rereconciled,
        )

        return results


def _env(key: str, default: str) -> str:
    """Get env var (import here to avoid circular deps)."""
    import os

    return os.environ.get(key, default)


async def run_reconcile_job(
    ledger_path: str | None = None,
    since_days: int = 7,
    riskcast_ingest_url: str | None = None,
    api_key: str | None = None,
) -> list[ReconcileResult]:
    """
    Entry point for reconcile job.

    Usage:
        python -m riskcast.jobs.reconcile_job
        python -m riskcast.jobs.reconcile_job --loop --interval 300

    Env: RISKCAST_LEDGER_BASE_PATH, RISKCAST_INGEST_URL, RISKCAST_API_KEYS (first key).
    """
    ledger_path = ledger_path or _env("RISKCAST_LEDGER_BASE_PATH", "/var/lib/omen/ledger")
    ingest_url = riskcast_ingest_url or _env(
        "RISKCAST_INGEST_URL", "http://localhost:8001/api/v1/signals/ingest"
    )
    key = api_key
    if key is None:
        keys = _env("RISKCAST_API_KEYS", "riskcast-internal-key").strip().split(",")
        key = keys[0].strip() if keys else "riskcast-internal-key"

    ledger = LedgerClient(ledger_path)
    signal_store = get_store()
    reconcile_store = get_reconcile_store()

    job = ReconcileJob(
        ledger_client=ledger,
        signal_store=signal_store,
        reconcile_store=reconcile_store,
        riskcast_ingest_url=ingest_url,
        api_key=key,
    )

    results = await job.run(since_days=since_days)

    failed = [r for r in results if r.status == ReconcileStatus.FAILED]
    if failed:
        logger.error("Reconcile failed for %s partitions", len(failed))

    return results


if __name__ == "__main__":
    import argparse
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    parser = argparse.ArgumentParser(description="RiskCast reconcile job")
    parser.add_argument(
        "--loop",
        action="store_true",
        help="Run reconcile in a loop",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=300,
        metavar="SECONDS",
        help="Seconds between reconcile runs when --loop (default: 300)",
    )
    parser.add_argument(
        "--ledger-path",
        type=str,
        default=None,
        help="Ledger base path (default: RISKCAST_LEDGER_BASE_PATH or /var/lib/omen/ledger)",
    )
    parser.add_argument(
        "--since-days",
        type=int,
        default=7,
        help="Reconcile partitions from last N days (default: 7)",
    )
    args = parser.parse_args()

    if args.loop:
        logger.info("Reconcile job starting in loop mode (interval=%ss)", args.interval)

        async def loop_run() -> None:
            while True:
                try:
                    await run_reconcile_job(
                        ledger_path=args.ledger_path,
                        since_days=args.since_days,
                    )
                except Exception as e:
                    logger.exception("Reconcile run failed: %s", e)
                await asyncio.sleep(args.interval)

        asyncio.run(loop_run())
    else:
        results = asyncio.run(
            run_reconcile_job(
                ledger_path=args.ledger_path,
                since_days=args.since_days,
            )
        )
        failed = [r for r in results if r.status == ReconcileStatus.FAILED]
        if failed:
            sys.exit(1)
        sys.exit(0)
