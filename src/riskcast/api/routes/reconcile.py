"""
Reconcile API

Endpoints for manual reconcile and status checking.
"""

import logging
from typing import Optional

import aiosqlite
from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel

from riskcast.infrastructure.reconcile_state import get_reconcile_store
from riskcast.infrastructure.signal_store import get_store
from riskcast.jobs.reconcile_job import (
    LedgerClient,
    ReconcileJob,
    ReconcileResult,
    ReconcileStatus,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/reconcile", tags=["reconcile"])


class ReconcileRequest(BaseModel):
    """Manual reconcile request."""

    partition_date: Optional[str] = None  # Specific partition or None for all
    since_days: int = 7
    force: bool = False  # Force even if up to date (reserved)


class ReconcileResponse(BaseModel):
    """Reconcile response."""

    status: str
    message: str
    results: Optional[list[dict]] = None


class PartitionStatusResponse(BaseModel):
    """Partition reconcile status."""

    partition_date: str
    last_reconcile_at: Optional[str]
    ledger_highwater: int
    current_highwater: int
    needs_reconcile: bool
    reason: str


@router.post("/run")
async def run_reconcile(
    request: ReconcileRequest,
    background_tasks: BackgroundTasks,
) -> ReconcileResponse:
    """
    Trigger reconcile job.

    Can run for specific partition or all partitions.
    """
    ledger = LedgerClient("/var/lib/omen/ledger")
    signal_store = get_store()
    reconcile_store = get_reconcile_store()

    job = ReconcileJob(
        ledger_client=ledger,
        signal_store=signal_store,
        reconcile_store=reconcile_store,
        riskcast_ingest_url="http://localhost:8001/api/v1/signals/ingest",
        api_key="riskcast-internal-key",
    )

    if request.partition_date:
        result = await job.reconcile_partition(request.partition_date)
        return ReconcileResponse(
            status=result.status.value,
            message=f"Reconciled {request.partition_date}",
            results=[
                {
                    "partition": result.partition,
                    "status": result.status.value,
                    "missing": result.missing_count,
                    "replayed": result.replayed_count,
                }
            ],
        )
    else:

        async def run_full_reconcile() -> None:
            await job.run(since_days=request.since_days)

        background_tasks.add_task(run_full_reconcile)

        return ReconcileResponse(
            status="STARTED",
            message=f"Reconcile job started for last {request.since_days} days",
        )


@router.get("/status/{partition_date}")
async def get_partition_status(
    partition_date: str,
) -> PartitionStatusResponse:
    """
    Get reconcile status for a partition.

    Shows if partition needs reconcile and why.
    """
    ledger = LedgerClient("/var/lib/omen/ledger")
    reconcile_store = get_reconcile_store()

    current_highwater, current_revision = ledger.get_highwater(partition_date)
    state = await reconcile_store.get_state(partition_date)

    needs_reconcile, reason = await reconcile_store.needs_reconcile(
        partition_date,
        current_highwater,
        current_revision,
    )

    return PartitionStatusResponse(
        partition_date=partition_date,
        last_reconcile_at=(state.last_reconcile_at.isoformat() if state else None),
        ledger_highwater=state.ledger_highwater if state else 0,
        current_highwater=current_highwater,
        needs_reconcile=needs_reconcile,
        reason=reason,
    )


@router.get("/history/{partition_date}")
async def get_reconcile_history(
    partition_date: str,
    limit: int = 10,
) -> list[dict]:
    """Get reconcile history for a partition."""
    reconcile_store = get_reconcile_store()

    async with aiosqlite.connect(reconcile_store.db_path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT * FROM reconcile_history
            WHERE partition_date = ?
            ORDER BY reconcile_at DESC
            LIMIT ?
            """,
            (partition_date, limit),
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
