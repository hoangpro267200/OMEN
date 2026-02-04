"""
UI API — endpoints for demo frontend Live mode.
Overview uses real pipeline metrics and activity; other routes are stubs until ledger/riskcast integration.

Security: Requires appropriate scopes for each endpoint.
"""

from datetime import datetime
from fastapi import APIRouter, Depends, Query

from omen.infrastructure.activity.activity_logger import get_activity_logger
from omen.infrastructure.metrics.pipeline_metrics import get_metrics_collector
from omen.api.route_dependencies import (
    require_signals_read,
    require_stats_read,
    require_storage_read,
    require_storage_write,
)
from omen.infrastructure.security.unified_auth import AuthContext

router = APIRouter()


def _format_time_short(iso_ts: str) -> str:
    """Format ISO timestamp to HH:MM:SS for activity feed."""
    try:
        dt = datetime.fromisoformat(iso_ts.replace("Z", "+00:00"))
        return dt.strftime("%H:%M:%S")
    except Exception:
        return iso_ts[:19] if len(iso_ts) >= 19 else iso_ts


@router.get("/overview")
async def get_overview(
    auth: AuthContext = Depends(require_stats_read),  # RBAC: read:stats
):
    """
    Overview stats for dashboard KPIs.
    Uses real pipeline metrics and activity; partitions/reconcile are 0 until ledger/riskcast integrated.
    """
    metrics = get_metrics_collector()
    stats = metrics.get_stats()
    logger = get_activity_logger()
    events = logger.get_recent(limit=50)

    signals_today = stats.get("active_signals", 0) or stats.get("signals_generated", 0)
    events_processed = stats.get("events_processed", 0)
    events_validated = stats.get("events_validated", 0)
    events_rejected = stats.get("events_rejected", 0)
    validation_rate = stats.get("validation_rate", 0.0)
    hot_path_ok = events_validated
    hot_path_pct = f"{validation_rate * 100:.1f}%" if events_processed else "0%"

    activity_feed = [
        {
            "time": _format_time_short(e.get("timestamp", "")),
            "id": e.get("id", ""),
            "status": e.get("type", "system"),
            "channel": (e.get("message", ""))[:60],
        }
        for e in events
    ]

    return {
        "signals_today": signals_today,
        "signals_trend": "—",
        "signals_trend_up": False,
        "hot_path_ok": hot_path_ok,
        "hot_path_pct": hot_path_pct,
        "duplicates": events_rejected,
        "duplicates_sub": f"({events_rejected} rejected)" if events_rejected else "",
        "partitions_sealed": 0,
        "partitions_open": 0,
        "partitions_sub": "—",
        "last_reconcile": "—",
        "last_reconcile_status": "—",
        "activity_feed": activity_feed,
    }


@router.get("/partitions")
async def list_partitions(
    date_from: str | None = Query(None, alias="date_from"),
    date_to: str | None = Query(None, alias="date_to"),
    status: str | None = None,
    includeLate: bool | None = Query(None, alias="includeLate"),
    needsReconcile: bool | None = Query(None, alias="needsReconcile"),
    auth: AuthContext = Depends(require_storage_read),  # RBAC: read:storage
):
    """List ledger partitions.
    
    NOT IMPLEMENTED: Requires ledger storage integration.
    Returns empty list as stub for frontend compatibility.
    """
    # TODO: Implement with real ledger integration
    return []


@router.get("/partitions/{partition_date}")
async def get_partition_detail(
    partition_date: str,
    auth: AuthContext = Depends(require_storage_read),  # RBAC: read:storage
):
    """Partition detail.
    
    NOT IMPLEMENTED: Requires ledger storage integration.
    Returns null as stub for frontend compatibility.
    """
    # TODO: Implement with real ledger integration
    return None


@router.get("/partitions/{partition_date}/diff")
async def get_partition_diff(
    partition_date: str,
    auth: AuthContext = Depends(require_storage_read),  # RBAC: read:storage
):
    """Partition diff.
    
    NOT IMPLEMENTED: Requires ledger storage integration.
    Returns empty diff as stub for frontend compatibility.
    """
    # TODO: Implement with real ledger integration
    return {
        "ledger_ids": [],
        "processed_ids": [],
        "missing_ids": [],
    }


@router.post("/partitions/{partition_date}/reconcile")
async def run_reconcile(
    partition_date: str,
    auth: AuthContext = Depends(require_storage_write),  # RBAC: write:storage
):
    """Run reconcile.
    
    NOT IMPLEMENTED: Requires ledger storage and RiskCast integration.
    Returns SKIPPED status as stub for frontend compatibility.
    """
    # TODO: Implement with real ledger + RiskCast integration
    return {
        "status": "SKIPPED",
        "partition_date": partition_date,
        "ledger_count": 0,
        "processed_count": 0,
        "missing_count": 0,
        "replayed_count": 0,
        "replayed_ids": [],
        "duration_ms": 0,
        "reason": "Stub: no ledger data",
    }


@router.get("/signals")
async def list_signals(
    partition: str | None = None,
    category: str | None = None,
    confidence: str | None = None,
    search: str | None = None,
    limit: int | None = Query(None),
    auth: AuthContext = Depends(require_signals_read),  # RBAC: read:signals
):
    """List signals (stub: empty list)."""
    return []


@router.get("/ledger/{partition_date}/segments")
async def list_ledger_segments(
    partition_date: str,
    auth: AuthContext = Depends(require_storage_read),  # RBAC: read:storage
):
    """List ledger segments (stub: empty)."""
    return {
        "partition_date": partition_date,
        "segments": [],
    }


@router.get(
    "/ledger/{partition_date}/segments/{segment_file}/frames/{frame_index:int}",
)
async def read_ledger_frame(
    partition_date: str,
    segment_file: str,
    frame_index: int,
    auth: AuthContext = Depends(require_storage_read),  # RBAC: read:storage
):
    """Read one ledger frame (stub)."""
    return {
        "partition_date": partition_date,
        "segment_file": segment_file,
        "frame_index": frame_index,
        "payload_length": 0,
        "crc32_hex": "0x00000000",
        "crc_ok": False,
        "payload_preview": "",
        "byte_offset": 0,
    }


@router.post(
    "/ledger/{partition_date}/segments/{segment_file}/simulate-crash-tail",
)
async def simulate_crash_tail(
    partition_date: str,
    segment_file: str,
    body: dict | None = None,
    auth: AuthContext = Depends(require_storage_write),  # RBAC: write:storage
):
    """Crash-tail simulation (stub: not supported)."""
    return {
        "supported": False,
        "partition_date": partition_date,
        "segment_file": segment_file,
        "before_frames": [],
        "after_truncate_frames": [],
        "reader_result": {
            "returned_frames": [],
            "warnings": ["Not implemented in backend"],
            "returned_count": 0,
        },
        "proof": {"ok": False, "summary": "Not implemented"},
    }
