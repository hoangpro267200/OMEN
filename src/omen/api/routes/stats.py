"""
System statistics endpoint — values from real pipeline execution.

No hardcoded metrics. When the pipeline has not run, counts are 0 and notes explain.
"""

from typing import Any, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from omen.infrastructure.metrics.pipeline_metrics import get_metrics_collector

try:
    import psutil
except ImportError:
    psutil = None

router = APIRouter(prefix="/stats", tags=["Statistics"])


class SystemStatsResponse(BaseModel):
    """
    System statistics — from actual pipeline execution.

    All counts and latency come from the metrics collector.
    """

    active_signals: int = Field(description="Signals in the measurement window")
    critical_alerts: int = Field(description="Estimated high-severity signals")
    avg_confidence: float = Field(description="Weighted average confidence of generated signals")
    total_risk_exposure: float = Field(description="Total risk exposure in USD")
    events_processed: int = Field(description="Lifetime events received")
    events_validated: int = Field(description="Lifetime events that passed validation")
    signals_generated: int = Field(description="Lifetime signals emitted")
    events_rejected: int = Field(description="Lifetime events rejected")
    validation_rate: float = Field(description="events_validated / events_processed")
    system_latency_ms: float = Field(description="Average processing latency (ms)")
    events_per_minute: float = Field(description="Processing rate in window")
    uptime_seconds: int = Field(description="Seconds since collector start")
    memory_usage_mb: int = Field(default=0, description="Process RSS in MB")
    cpu_percent: float = Field(default=0.0, description="CPU usage percent")
    polymarket_status: str = Field(default="unknown", description="Source status when available")
    polymarket_events_per_min: float = Field(default=0.0, description="Source rate when available")


@router.get("", response_model=SystemStatsResponse)
async def get_system_stats() -> SystemStatsResponse:
    """
    Get current system statistics.

    All values are from real pipeline execution. When no processing has run,
    counts are 0 and latency/confidence are 0.
    """
    metrics = get_metrics_collector()
    stats: dict[str, Any] = metrics.get_stats()

    memory_mb = 0
    cpu_pct = 0.0
    if psutil is not None:
        try:
            memory_mb = int(psutil.Process().memory_info().rss / 1024 / 1024)
            cpu_pct = float(psutil.cpu_percent())
        except Exception:
            pass

    source_health = stats.get("source_health") or {}
    poly = source_health.get("polymarket", {})
    polymarket_status = "connected" if poly.get("status") == "connected" else (poly.get("status") or "unknown")
    polymarket_events_per_min = float(poly.get("events_per_minute") or 0)

    return SystemStatsResponse(
        active_signals=stats.get("active_signals", 0),
        critical_alerts=stats.get("critical_alerts", 0),
        avg_confidence=stats.get("avg_confidence", 0.0),
        total_risk_exposure=stats.get("total_risk_exposure", 0.0),
        events_processed=stats.get("events_processed", 0),
        events_validated=stats.get("events_validated", 0),
        signals_generated=stats.get("signals_generated", 0),
        events_rejected=stats.get("events_rejected", 0),
        validation_rate=stats.get("validation_rate", 0.0),
        system_latency_ms=stats.get("system_latency_ms", 0.0),
        events_per_minute=stats.get("events_per_minute", 0.0),
        uptime_seconds=stats.get("uptime_seconds", 0),
        memory_usage_mb=memory_mb,
        cpu_percent=cpu_pct,
        polymarket_status=polymarket_status,
        polymarket_events_per_min=polymarket_events_per_min,
    )
