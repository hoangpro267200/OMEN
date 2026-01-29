"""Signal endpoints (require API key via router dependencies)."""

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


@router.get("/stats", response_model=PipelineStatsResponse)
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


@router.post("/process", response_model=SignalListResponse)
async def process_events_to_signals(
    limit: int = Query(default=100, le=500),
    min_liquidity: float = Query(default=1000),
    min_confidence: float = Query(default=0.0),
    pipeline: SignalOnlyPipeline = Depends(get_signal_only_pipeline),
    _api_key: str = Depends(verify_api_key),
) -> SignalListResponse:
    """
    Fetch events, run signal-only pipeline (validate → enrich → signal), return structured signals.

    This is the Signal Intelligence contract: probability, confidence, context, evidence.
    No impact calculations, no recommendations, no time-horizon or high-confidence flags.
    """
    from omen.adapters.inbound.polymarket.source import PolymarketSignalSource
    from omen.domain.errors import SourceUnavailableError

    try:
        source = PolymarketSignalSource(logistics_only=True)
        raw_list = list(source.fetch_events(limit=min(limit * 2, 1000)))
        filtered = [
            e for e in raw_list
            if e.market.current_liquidity_usd >= min_liquidity
        ][:limit]
        results = pipeline.process_batch(filtered)
        signals_out = [
            _pure_signal_to_response(r.signal)
            for r in results
            if r.success and r.signal is not None and r.signal.confidence_score >= min_confidence
        ]
        n = len(results)
        passed = sum(1 for r in results if r.success and r.signal is not None)
        return SignalListResponse(
            signals=signals_out,
            total=len(signals_out),
            processed=n,
            passed=passed,
            rejected=n - passed,
            pass_rate=(passed / n) if n else 0.0,
        )
    except SourceUnavailableError as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.get("/")
async def list_signals(
    limit: int = Query(default=100, le=1000),
    offset: int = Query(default=0, ge=0),
    since: datetime | None = Query(default=None),
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


@router.get("/{signal_id}")
async def get_signal(
    signal_id: str,
    detail_level: Literal["minimal", "standard", "full"] = "standard",
    repository: SignalRepository = Depends(get_repository),
    _api_key: str = Depends(verify_api_key),
) -> dict:
    """Get a single signal by ID."""
    signal = repository.find_by_id(signal_id)
    if not signal:
        raise HTTPException(status_code=404, detail="Signal not found")
    return redact_for_api(signal, detail_level=detail_level)
