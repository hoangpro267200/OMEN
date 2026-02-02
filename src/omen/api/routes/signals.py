"""Signal endpoints with RBAC enforcement.

- GET endpoints require: read:signals
- POST endpoints require: write:signals
"""

from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query

from omen.api.dependencies import get_repository, get_signal_only_pipeline
from omen.api.models.responses import (
    EvidenceResponse,
    GeographicContextResponse,
    PipelineStatsResponse,
    SignalListResponse,
    SignalResponse,
    TemporalContextResponse,
)
from omen.application.ports.signal_repository import SignalRepository
from omen.application.signal_pipeline import SignalOnlyPipeline
from omen.domain.models.omen_signal import OmenSignal
from omen.infrastructure.debug.rejection_tracker import get_rejection_tracker
from omen.infrastructure.security.auth import verify_api_key
from omen.infrastructure.security.rbac import Scopes, require_scopes
from omen.infrastructure.security.redaction import redact_for_api

router = APIRouter()


def _pure_signal_to_response(signal: OmenSignal) -> SignalResponse:
    """Convert pure OmenSignal to API SignalResponse."""
    return SignalResponse(
        signal_id=signal.signal_id,
        source_event_id=signal.source_event_id,
        title=signal.title,
        description=signal.description,
        probability=signal.probability,
        probability_source=signal.probability_source,
        probability_is_estimate=signal.probability_is_estimate,
        confidence_score=signal.confidence_score,
        confidence_level=signal.confidence_level.value,
        confidence_factors=signal.confidence_factors,
        category=signal.category.value,
        tags=signal.tags,
        geographic=GeographicContextResponse(
            regions=signal.geographic.regions,
            chokepoints=signal.geographic.chokepoints,
        ),
        temporal=TemporalContextResponse(
            event_horizon=signal.temporal.event_horizon,
            resolution_date=(
                signal.temporal.resolution_date.isoformat()
                if signal.temporal.resolution_date
                else None
            ),
        ),
        evidence=[
            EvidenceResponse(source=e.source, source_type=e.source_type, url=e.url)
            for e in signal.evidence
        ],
        trace_id=signal.trace_id,
        ruleset_version=signal.ruleset_version,
        source_url=signal.source_url,
        generated_at=signal.generated_at.isoformat(),
    )


@router.get(
    "/stats",
    response_model=PipelineStatsResponse,
    summary="Get pipeline statistics",
    description="""
Get pipeline processing statistics for the signal-only path.

Returns counts, pass rates, and latency metrics. No impact or recommendation data.

**Example Response:**
```json
{
    "total_processed": 1500,
    "total_passed": 1250,
    "total_rejected": 250,
    "pass_rate": 0.833,
    "rejection_by_stage": {
        "liquidity": 150,
        "semantic": 60,
        "geographic": 40
    },
    "latency_ms": 45,
    "uptime_seconds": 86400
}
```
    """,
    responses={
        200: {
            "description": "Pipeline statistics",
            "content": {
                "application/json": {
                    "example": {
                        "total_processed": 1500,
                        "total_passed": 1250,
                        "total_rejected": 250,
                        "pass_rate": 0.833,
                        "rejection_by_stage": {"liquidity": 150, "semantic": 60, "geographic": 40},
                        "latency_ms": 45,
                        "uptime_seconds": 86400
                    }
                }
            }
        }
    },
)
async def get_signal_stats(
    _api_key: str = Depends(verify_api_key),
) -> PipelineStatsResponse:
    """
    Get pipeline processing statistics for the signal-only path.

    Returns counts and pass rate; no impact or recommendation data.
    """
    tracker = get_rejection_tracker()
    stats = tracker.get_statistics()
    by_stage = (
        stats.get("by_stage")
        if isinstance(stats.get("by_stage"), dict)
        else {}
    )
    rejection_by_stage: dict[str, int] = {}
    if by_stage:
        for stage, data in by_stage.items():
            if isinstance(data, dict) and "count" in data:
                rejection_by_stage[stage] = int(data["count"])
            else:
                rejection_by_stage[stage] = int(data) if isinstance(data, (int, float)) else 0
    return PipelineStatsResponse(
        total_processed=stats.get("total_processed", 0),
        total_passed=stats.get("total_passed", 0),
        total_rejected=stats.get("total_rejected", 0),
        pass_rate=stats.get("pass_rate", 0.0),
        rejection_by_stage=rejection_by_stage,
        latency_ms=stats.get("latency_ms", 0),
        uptime_seconds=stats.get("uptime_seconds", 0),
    )


@router.post(
    "/batch",
    response_model=SignalListResponse,
    dependencies=[Depends(require_scopes([Scopes.WRITE_SIGNALS]))],  # 🔒 RBAC: write:signals
)
async def create_signals_batch(
    limit: int = Query(default=100, le=500),
    min_liquidity: float = Query(default=1000),
    min_confidence: float = Query(default=0.0),
    pipeline: SignalOnlyPipeline = Depends(get_signal_only_pipeline),
    repository: SignalRepository = Depends(get_repository),
    _api_key: str = Depends(verify_api_key),
) -> SignalListResponse:
    """
    Fetch events, run signal-only pipeline (validate → enrich → signal), return structured signals.

    This is the Signal Intelligence contract: probability, confidence, context, evidence.
    No impact calculations, no recommendations, no time-horizon or high-confidence flags.
    """
    import time
    from omen.adapters.inbound.polymarket.source import PolymarketSignalSource
    from omen.domain.errors import SourceUnavailableError
    from omen.infrastructure.metrics.pipeline_metrics import get_metrics_collector
    from omen.infrastructure.activity.activity_logger import get_activity_logger

    metrics = get_metrics_collector()
    activity = get_activity_logger()
    start_time = time.perf_counter()

    try:
        source = PolymarketSignalSource(logistics_only=False)
        raw_list = list(source.fetch_events(limit=min(limit * 2, 1000)))
        
        # Update source health and log fetch
        fetch_time = (time.perf_counter() - start_time) * 1000
        metrics.update_source_health(
            source_name="polymarket",
            status="connected",
            events_fetched=len(raw_list),
            latency_ms=fetch_time,
            error=False,
        )
        activity.log_source_fetch(
            source_name="Polymarket",
            events_count=len(raw_list),
            latency_ms=fetch_time,
            success=True,
        )
        
        filtered = [
            e for e in raw_list
            if e.market.current_liquidity_usd >= min_liquidity
        ][:limit]
        
        results = pipeline.process_batch(filtered)
        
        signals_out = []
        valid_signals = []
        for r in results:
            if r.success and r.signal is not None and r.signal.confidence_score >= min_confidence:
                signals_out.append(_pure_signal_to_response(r.signal))
                valid_signals.append(r.signal)
                # Save to repository
                repository.save(r.signal)
                # Log signal generation
                activity.log_signal_generated(
                    signal_id=r.signal.signal_id,
                    title=r.signal.title,
                    confidence_label=r.signal.confidence_level.value,
                    confidence_level=str(r.signal.confidence_score),
                )
        
        n = len(results)
        passed = sum(1 for r in results if r.success and r.signal is not None)
        rejected = n - passed
        
        # Record metrics
        processing_time = (time.perf_counter() - start_time) * 1000
        metrics.record_from_pipeline_result(
            events_received=n,
            events_validated=passed,
            events_rejected=rejected,
            signals_generated=len(signals_out),
            processing_time_ms=processing_time,
            signals=valid_signals,
        )
        
        # Log system event for summary
        activity.log_system_event(
            f"Pipeline processed {n} events → {len(signals_out)} signals ({rejected} rejected)"
        )
        
        return SignalListResponse(
            signals=signals_out,
            total=len(signals_out),
            processed=n,
            passed=passed,
            rejected=rejected,
            pass_rate=(passed / n) if n else 0.0,
        )
    except SourceUnavailableError as e:
        metrics.update_source_health(
            source_name="polymarket",
            status="disconnected",
            events_fetched=0,
            latency_ms=0,
            error=True,
        )
        activity.log_source_fetch(
            source_name="Polymarket",
            events_count=0,
            latency_ms=0,
            success=False,
            error_message=str(e),
        )
        raise HTTPException(status_code=503, detail=str(e))


@router.get(
    "/",
    summary="List recent signals",
    description="""
List recent signals with pagination.

**Query Parameters:**
- `limit`: Max signals to return (default: 100, max: 1000)
- `offset`: Pagination offset (default: 0)
- `since`: Only return signals after this timestamp (ISO 8601)

**Example Request:**
```
GET /api/v1/signals/?limit=10&since=2026-01-01T00:00:00Z
```

**Response includes:**
- List of redacted signals
- Pagination metadata (total, limit, offset)
    """,
    responses={
        200: {
            "description": "List of signals",
            "content": {
                "application/json": {
                    "example": {
                        "signals": [
                            {
                                "signal_id": "OMEN-A1B2C3D4E5F6",
                                "title": "Red Sea shipping disruption probability",
                                "probability": 0.72,
                                "confidence_level": "HIGH",
                                "confidence_score": 0.85,
                                "category": "GEOPOLITICAL",
                                "trace_id": "a1b2c3d4e5f6g7h8"
                            }
                        ],
                        "total": 150,
                        "limit": 100,
                        "offset": 0
                    }
                }
            }
        }
    },
)
async def list_signals(
    limit: int = Query(default=100, le=1000, description="Maximum number of signals to return"),
    offset: int = Query(default=0, ge=0, description="Pagination offset"),
    since: datetime | None = Query(default=None, description="Only return signals after this timestamp"),
    repository: SignalRepository = Depends(get_repository),
    _api_key: str = Depends(verify_api_key),
) -> dict:
    """
    List recent signals with pagination.

    Returns redacted signals plus total, limit, and offset.
    """
    signals = repository.find_recent(limit=limit, offset=offset, since=since)
    total = repository.count(since=since)
    return {
        "signals": [redact_for_api(s) for s in signals],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get(
    "/{signal_id}",
    summary="Get signal by ID",
    description="""
Get a single signal by its unique identifier.

**Detail Levels:**
- `minimal`: Basic fields only (signal_id, title, probability, confidence_level)
- `standard`: Default - includes evidence and geographic context
- `full`: All fields including confidence breakdown

**Example Request:**
```
GET /api/v1/signals/OMEN-A1B2C3D4E5F6?detail_level=full
```
    """,
    responses={
        200: {
            "description": "Signal details",
            "content": {
                "application/json": {
                    "example": {
                        "signal_id": "OMEN-A1B2C3D4E5F6",
                        "source_event_id": "poly-12345",
                        "title": "Red Sea shipping disruption probability increases",
                        "probability": 0.72,
                        "probability_source": "polymarket",
                        "confidence_score": 0.85,
                        "confidence_level": "HIGH",
                        "confidence_factors": {
                            "liquidity": 0.9,
                            "geographic": 0.85,
                            "source_reliability": 0.8
                        },
                        "category": "GEOPOLITICAL",
                        "geographic": {
                            "regions": ["Middle East", "Red Sea"],
                            "chokepoints": ["bab-el-mandeb", "suez"]
                        },
                        "temporal": {
                            "event_horizon": "2026-06-30",
                            "resolution_date": "2026-06-30T00:00:00Z"
                        },
                        "evidence": [
                            {
                                "source": "Polymarket",
                                "source_type": "market",
                                "url": "https://polymarket.com/market/xyz"
                            }
                        ],
                        "trace_id": "a1b2c3d4e5f6g7h8",
                        "generated_at": "2026-02-01T12:00:00Z"
                    }
                }
            }
        },
        404: {
            "description": "Signal not found",
            "content": {
                "application/json": {
                    "example": {
                        "error": "NOT_FOUND",
                        "message": "Signal 'OMEN-INVALID' not found",
                        "hint": "Verify the signal ID is correct and exists"
                    }
                }
            }
        }
    },
)
async def get_signal(
    signal_id: str,
    detail_level: Literal["minimal", "standard", "full"] = Query(
        default="standard",
        description="Level of detail to include in response"
    ),
    repository: SignalRepository = Depends(get_repository),
    _api_key: str = Depends(verify_api_key),
) -> dict[str, object]:
    """Get a single signal by ID."""
    signal = repository.find_by_id(signal_id)
    if not signal:
        raise HTTPException(status_code=404, detail="Signal not found")
    return redact_for_api(signal, detail_level=detail_level)
