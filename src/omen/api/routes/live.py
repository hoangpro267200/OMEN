"""
Live Polymarket data endpoints for demo UI.

Fetches from Gamma API, runs OMEN pipeline, returns results for the React app.
"""

from datetime import datetime

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from omen.application.container import get_container
from omen.domain.errors import SourceUnavailableError
from omen.adapters.inbound.polymarket.source import PolymarketSignalSource


router = APIRouter(prefix="/live", tags=["Live Data"])


class LiveEventResponse(BaseModel):
    """One live event summary for the UI."""
    event_id: str
    title: str
    probability: float
    liquidity_usd: float
    volume_usd: float
    keywords: list[str]
    source_url: str | None
    observed_at: datetime


class ProcessedSignalResponse(BaseModel):
    """Processed OMEN signal for the UI (matches OmenSignal-style shape)."""
    signal_id: str
    event_id: str
    title: str
    current_probability: float
    probability_momentum: str
    confidence_level: str
    confidence_score: float
    severity: float
    severity_label: str
    is_actionable: bool
    urgency: str
    key_metrics: list[dict]
    affected_routes: list[dict]
    explanation_chain: dict


def _signal_to_response(s) -> dict:
    """Map OmenSignal to UI-friendly dict."""
    def metric_dict(m):
        out = {"name": m.name, "value": m.value, "unit": m.unit}
        if getattr(m, "uncertainty", None) is not None:
            u = m.uncertainty
            out["uncertainty"] = {"lower": u.lower, "upper": u.upper}
        if getattr(m, "evidence_source", None):
            out["evidence_source"] = m.evidence_source
        return out

    def route_dict(r):
        out = {
            "route_id": r.route_id,
            "route_name": r.route_name,
            "origin_region": r.origin_region,
            "destination_region": r.destination_region,
            "impact_severity": r.impact_severity,
        }
        return out

    chain = s.explanation_chain
    steps = [
        {
            "step_id": st.step_id,
            "rule_name": st.rule_name,
            "rule_version": st.rule_version,
            "status": "passed",
            "reasoning": st.reasoning,
            "confidence_contribution": st.confidence_contribution,
        }
        for st in chain.steps
    ]

    return ProcessedSignalResponse(
        signal_id=s.signal_id,
        event_id=str(s.event_id),
        title=s.title,
        current_probability=s.current_probability,
        probability_momentum=s.probability_momentum,
        confidence_level=s.confidence_level.value,
        confidence_score=s.confidence_score,
        severity=s.severity,
        severity_label=s.severity_label,
        is_actionable=s.is_actionable,
        urgency=s.urgency,
        key_metrics=[metric_dict(m) for m in s.key_metrics],
        affected_routes=[route_dict(r) for r in s.affected_routes],
        explanation_chain={
            "trace_id": chain.trace_id,
            "total_steps": chain.total_steps,
            "steps": steps,
        },
    )


@router.get("/events", response_model=list[LiveEventResponse])
async def get_live_events(
    limit: int = Query(default=20, le=100),
    logistics_only: bool = Query(default=True),
):
    """
    Fetch live events from Polymarket (raw, before OMEN processing).
    """
    try:
        source = PolymarketSignalSource(logistics_only=logistics_only)
        events: list[LiveEventResponse] = []
        for signal in source.fetch_events(limit=limit):
            events.append(
                LiveEventResponse(
                    event_id=str(signal.event_id),
                    title=signal.title,
                    probability=signal.probability,
                    liquidity_usd=signal.market.current_liquidity_usd,
                    volume_usd=signal.market.total_volume_usd,
                    keywords=signal.keywords,
                    source_url=signal.market.market_url,
                    observed_at=signal.observed_at,
                )
            )
        return events
    except SourceUnavailableError as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.get("/events/search")
async def search_events(
    query: str = Query(..., min_length=2),
    limit: int = Query(default=10, le=50),
):
    """Search Polymarket events by keyword."""
    try:
        source = PolymarketSignalSource(logistics_only=False)
        events = []
        for s in source.search(query, limit=limit):
            events.append({
                "event_id": str(s.event_id),
                "title": s.title,
                "probability": s.probability,
                "liquidity_usd": s.market.current_liquidity_usd,
                "keywords": s.keywords,
            })
            if len(events) >= limit:
                break
        return events[:limit]
    except SourceUnavailableError as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.post("/process", response_model=list[ProcessedSignalResponse])
async def process_live_events(
    limit: int = Query(default=10, le=50),
    min_liquidity: float = Query(default=1000),
):
    """
    Fetch live Polymarket events and run them through the OMEN pipeline.
    Returns processed signals for the demo UI.
    """
    try:
        container = get_container()
        pipeline = container.pipeline
        source = PolymarketSignalSource(logistics_only=True)
        raw_list = list(source.fetch_events(limit=limit * 2))
        filtered = [
            e for e in raw_list
            if e.market.current_liquidity_usd >= min_liquidity
        ][:limit]
        results = []
        for event in filtered:
            result = pipeline.process_single(event)
            if result.success and result.signals:
                for signal in result.signals:
                    results.append(_signal_to_response(signal))
        return results
    except SourceUnavailableError as e:
        raise HTTPException(status_code=503, detail=f"Polymarket unavailable: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/process-single")
async def process_single_event(
    event_id: str = Query(..., alias="event_id"),
):
    """
    Process a single event by ID and return one OMEN signal or rejection info.
    """
    try:
        source = PolymarketSignalSource(logistics_only=False)
        container = get_container()
        pipeline = container.pipeline
        signal = source.fetch_by_id(event_id)
        if signal is None:
            raise HTTPException(status_code=404, detail=f"Event {event_id!r} not found")
        res = pipeline.process_single(signal)
        if res.success and res.signals:
            return {
                "signal": _signal_to_response(res.signals[0]).model_dump(),
                "stats": (
                    {
                        "events_received": res.stats.events_received,
                        "events_validated": res.stats.events_validated,
                        "signals_generated": res.stats.signals_generated,
                    }
                    if res.stats else None
                ),
            }
        return {
            "signal": None,
            "rejection_reason": (
                res.validation_failures[0].reason
                if res.validation_failures else "No applicable rules"
            ),
        }
    except HTTPException:
        raise
    except SourceUnavailableError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
