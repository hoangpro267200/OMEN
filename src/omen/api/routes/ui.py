"""
UI API — endpoints for demo frontend Live mode.
Overview uses real pipeline metrics and activity; other routes are stubs until ledger/riskcast integration.

Security: Requires appropriate scopes for each endpoint.
"""

from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Query

from omen.infrastructure.activity.activity_logger import get_activity_logger
from omen.infrastructure.metrics.pipeline_metrics import get_metrics_collector
from omen.infrastructure.security.auth import verify_api_key
from omen.infrastructure.security.rbac import Scopes, require_scopes

router = APIRouter()

# Security dependencies
_read_stats = [Depends(verify_api_key), Depends(require_scopes([Scopes.READ_STATS]))]
_read_storage = [Depends(verify_api_key), Depends(require_scopes([Scopes.READ_STORAGE]))]
_write_storage = [Depends(verify_api_key), Depends(require_scopes([Scopes.WRITE_STORAGE]))]
_read_signals = [Depends(verify_api_key), Depends(require_scopes([Scopes.READ_SIGNALS]))]


def _format_time_short(iso_ts: str) -> str:
    """Format ISO timestamp to HH:MM:SS for activity feed."""
    try:
        dt = datetime.fromisoformat(iso_ts.replace("Z", "+00:00"))
        return dt.strftime("%H:%M:%S")
    except Exception:
        return iso_ts[:19] if len(iso_ts) >= 19 else iso_ts


@router.get("/overview", dependencies=_read_stats)
async def get_overview():
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


@router.get("/partitions", dependencies=_read_storage)
async def list_partitions(
    date_from: str | None = Query(None, alias="date_from"),
    date_to: str | None = Query(None, alias="date_to"),
    status: str | None = None,
    includeLate: bool | None = Query(None, alias="includeLate"),
    needsReconcile: bool | None = Query(None, alias="needsReconcile"),
):
    """List ledger partitions (stub: empty list)."""
    return []


@router.get("/partitions/{partition_date}", dependencies=_read_storage)
async def get_partition_detail(partition_date: str):
    """Partition detail (stub: null)."""
    return None


@router.get("/partitions/{partition_date}/diff", dependencies=_read_storage)
async def get_partition_diff(partition_date: str):
    """Partition diff (stub: empty)."""
    return {
        "ledger_ids": [],
        "processed_ids": [],
        "missing_ids": [],
    }


@router.post("/partitions/{partition_date}/reconcile", dependencies=_write_storage)
async def run_reconcile(partition_date: str):
    """Run reconcile (stub)."""
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


@router.get("/signals", dependencies=_read_signals)
async def list_signals(
    partition: str | None = None,
    category: str | None = None,
    confidence: str | None = None,
    search: str | None = None,
    limit: int | None = Query(None),
):
    """List signals (stub: empty list)."""
    return []


@router.get("/ledger/{partition_date}/segments", dependencies=_read_storage)
async def list_ledger_segments(partition_date: str):
    """List ledger segments (stub: empty)."""
    return {
        "partition_date": partition_date,
        "segments": [],
    }


@router.get("/ledger/{partition_date}/segments/{segment_file}/frames/{frame_index:int}", dependencies=_read_storage)
async def read_ledger_frame(partition_date: str, segment_file: str, frame_index: int):
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


@router.post("/ledger/{partition_date}/segments/{segment_file}/simulate-crash-tail", dependencies=_write_storage)
async def simulate_crash_tail(partition_date: str, segment_file: str, body: dict | None = None):
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
