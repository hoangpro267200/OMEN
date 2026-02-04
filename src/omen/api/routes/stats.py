"""
System statistics — signal-quality metrics only.

No impact metrics (no high-confidence counts as alerts, risk quantification, severity, or time-horizon labels).
"""

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from omen.api.route_dependencies import require_stats_read
from omen.infrastructure.metrics.pipeline_metrics import get_metrics_collector
from omen.infrastructure.security.unified_auth import AuthContext
from omen.domain.services import get_quality_metrics, get_historical_validator

try:
    import psutil
except ImportError:
    psutil = None

router = APIRouter(prefix="/stats", tags=["Statistics"])


class SystemStatsResponse(BaseModel):
    """
    Signal-quality statistics only.

    Does NOT include: impact metrics, risk quantification, severity, or time-horizon labels.
    """

    total_signals: int = Field(description="Signals in the measurement window")
    signals_by_confidence: dict[str, int] = Field(
        default_factory=dict,
        description="Count by confidence level: HIGH, MEDIUM, LOW",
    )
    signals_by_category: dict[str, int] = Field(
        default_factory=dict,
        description="Count by signal category",
    )
    average_confidence_score: float = Field(
        description="Weighted average confidence of generated signals (0-1)",
    )
    signals_with_high_probability: int = Field(
        default=0,
        description="Signals with probability > 0.7",
    )
    signals_with_low_confidence: int = Field(
        default=0,
        description="Signals with confidence < 0.5",
    )
    validation_pass_rate: float = Field(
        description="events_validated / events_processed",
    )
    signals_by_time_horizon: dict[str, int] = Field(
        default_factory=dict,
        description="Count by horizon: 24h, 7d, 30d (when available)",
    )
    events_processed: int = Field(description="Lifetime events received")
    events_validated: int = Field(description="Lifetime events that passed validation")
    signals_generated: int = Field(description="Lifetime signals emitted")
    events_rejected: int = Field(description="Lifetime events rejected")
    system_latency_ms: float = Field(description="Average processing latency (ms)")
    events_per_minute: float = Field(description="Processing rate in window")
    uptime_seconds: int = Field(description="Seconds since collector start")
    memory_usage_mb: int = Field(default=0, description="Process RSS in MB")
    cpu_percent: float = Field(default=0.0, description="CPU usage percent")
    polymarket_status: str = Field(
        default="unknown",
        description="Source status when available",
    )
    polymarket_events_per_min: float = Field(
        default=0.0,
        description="Source rate when available",
    )


@router.get("", response_model=SystemStatsResponse)
async def get_system_stats(
    auth: AuthContext = Depends(require_stats_read),  # RBAC: read:stats
) -> SystemStatsResponse:
    """
    Get current system statistics (signal-quality only).

    No impact metrics. Values from real pipeline execution.
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
    polymarket_status = (
        "connected" if poly.get("status") == "connected" else (poly.get("status") or "unknown")
    )
    polymarket_events_per_min = float(poly.get("events_per_minute") or 0)

    return SystemStatsResponse(
        total_signals=stats.get("active_signals", 0),
        signals_by_confidence=stats.get("signals_by_confidence") or {},
        signals_by_category=stats.get("signals_by_category") or {},
        average_confidence_score=stats.get("avg_confidence", 0.0),
        signals_with_high_probability=stats.get("signals_with_high_probability", 0),
        signals_with_low_confidence=stats.get("signals_with_low_confidence", 0),
        validation_pass_rate=stats.get("validation_rate", 0.0),
        signals_by_time_horizon=stats.get("signals_by_time_horizon") or {},
        events_processed=stats.get("events_processed", 0),
        events_validated=stats.get("events_validated", 0),
        signals_generated=stats.get("signals_generated", 0),
        events_rejected=stats.get("events_rejected", 0),
        system_latency_ms=stats.get("system_latency_ms", 0.0),
        events_per_minute=stats.get("events_per_minute", 0.0),
        uptime_seconds=stats.get("uptime_seconds", 0),
        memory_usage_mb=memory_mb,
        cpu_percent=cpu_pct,
        polymarket_status=polymarket_status,
        polymarket_events_per_min=polymarket_events_per_min,
    )


class QualityMetricsResponse(BaseModel):
    """Quality metrics for signal validation calibration."""

    total_received: int = Field(description="Total events received")
    total_validated: int = Field(description="Events that passed validation")
    total_rejected: int = Field(description="Events that failed validation")
    rejection_rate: str = Field(description="Rejection rate as percentage")
    validation_rate: str = Field(description="Validation rate as percentage")
    avg_validation_score: str = Field(description="Average validation score")
    rejections_by_rule: dict[str, int] = Field(
        default_factory=dict,
        description="Rejection count by rule name",
    )
    rejections_by_status: dict[str, int] = Field(
        default_factory=dict,
        description="Rejection count by status",
    )
    confidence_distribution: dict[str, int] = Field(
        default_factory=dict,
        description="Signal count by confidence level",
    )


@router.get("/quality", response_model=QualityMetricsResponse)
async def get_quality_stats(
    auth: AuthContext = Depends(require_stats_read),  # RBAC: read:stats
) -> QualityMetricsResponse:
    """
    Get quality metrics for signal validation.
    
    Tracks validation outcomes for confidence calibration and quality monitoring.
    """
    quality = get_quality_metrics()
    data = quality.to_dict()
    
    return QualityMetricsResponse(
        total_received=data.get("total_received", 0),
        total_validated=data.get("total_validated", 0),
        total_rejected=data.get("total_rejected", 0),
        rejection_rate=data.get("rejection_rate", "0.0%"),
        validation_rate=data.get("validation_rate", "0.0%"),
        avg_validation_score=data.get("avg_validation_score", "0.00"),
        rejections_by_rule=data.get("rejections_by_rule", {}),
        rejections_by_status=data.get("rejections_by_status", {}),
        confidence_distribution=data.get("confidence_distribution", {}),
    )


class CalibrationResponse(BaseModel):
    """Calibration report for historical validation."""
    
    total_predictions: int = Field(description="Total predictions tracked")
    predictions_within_bounds: int = Field(description="Predictions within uncertainty bounds")
    coverage_rate: float = Field(description="Coverage rate (0-1)")
    mean_absolute_error: float = Field(description="Mean absolute error")
    mean_absolute_percent_error: float = Field(description="Mean absolute percent error")
    is_well_calibrated: bool = Field(description="Whether model is well-calibrated")
    errors_by_metric: dict[str, list[float]] = Field(
        default_factory=dict,
        description="Errors grouped by metric name",
    )


@router.get("/calibration", response_model=CalibrationResponse)
async def get_calibration_report(
    auth: AuthContext = Depends(require_stats_read),  # RBAC: read:stats
) -> CalibrationResponse:
    """
    Get calibration report comparing predictions vs actual outcomes.
    
    Use this to assess how well-calibrated OMEN's probability estimates are.
    """
    validator = get_historical_validator()
    results, report = validator.validate()
    
    return CalibrationResponse(
        total_predictions=report.total_predictions,
        predictions_within_bounds=report.predictions_within_bounds,
        coverage_rate=report.coverage_rate,
        mean_absolute_error=report.mean_absolute_error,
        mean_absolute_percent_error=report.mean_absolute_percent_error,
        is_well_calibrated=report.is_well_calibrated(),
        errors_by_metric=dict(report.errors_by_metric),
    )
