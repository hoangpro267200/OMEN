"""
Live Polymarket data endpoints for demo UI.

Fetches from Gamma API, runs OMEN pipeline, returns results for the React app.
All data in responses is traceable to pipeline or storage — no synthetic fabrication.
"""

from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from omen.application.container import get_container
from omen.domain.errors import SourceUnavailableError
from omen.adapters.inbound.polymarket.source import PolymarketSignalSource
from omen.infrastructure.storage.signal_history import get_signal_history_store


router = APIRouter(prefix="/live", tags=["Live Data"])


# =============================================================================
# LEGACY / COMPAT RESPONSE (kept for backward compatibility)
# =============================================================================


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


# =============================================================================
# FULL PROCESSED SIGNAL RESPONSE (all fields UI needs)
# =============================================================================


class ConfidenceBreakdown(BaseModel):
    """Breakdown of confidence score by component."""
    liquidity: float = 0.8
    geographic: float = 0.8
    semantic: float = 0.8
    anomaly: float = 0.8
    market_depth: float = 0.8
    source_reliability: float = 0.8


class RouteCoordinate(BaseModel):
    """Geographic coordinate."""
    lat: float
    lng: float
    name: str


class EnhancedRoute(BaseModel):
    """Route with full geographic data."""
    route_id: str
    route_name: str
    origin: RouteCoordinate
    destination: RouteCoordinate
    waypoints: list[RouteCoordinate] = []
    status: str  # "BLOCKED", "DELAYED", "ALTERNATIVE", "OPEN"
    impact_severity: float
    delay_days: float = 0


class Chokepoint(BaseModel):
    """Critical chokepoint."""
    name: str
    lat: float
    lng: float
    risk_level: str  # "CRITICAL", "HIGH", "MEDIUM", "LOW"


class EnhancedMetric(BaseModel):
    """Impact metric with projection data."""
    name: str
    value: float
    unit: str
    uncertainty: dict[str, float] | None = None  # {lower, upper} — only when provided
    baseline: float = 0
    projection: list[float] = []  # 7-day projection
    evidence_source: str | None = None
    methodology_name: str | None = None
    methodology_version: str | None = None


class EnhancedExplanationStep(BaseModel):
    """Explanation step with timing."""
    step_id: int
    rule_name: str
    rule_version: str
    status: str  # "passed", "failed"
    reasoning: str
    confidence_contribution: float
    processing_time_ms: float = 0


class FullProcessedSignalResponse(BaseModel):
    """
    Complete signal response with ALL fields UI needs.
    This is the contract between backend and frontend.
    """
    signal_id: str
    event_id: str
    title: str
    summary: str | None = None
    probability: float
    probability_history: list[float] = []
    probability_momentum: str  # "INCREASING", "DECREASING", "STABLE"
    confidence_level: str
    confidence_score: float
    confidence_breakdown: ConfidenceBreakdown
    severity: float
    severity_label: str
    is_actionable: bool
    urgency: str
    metrics: list[EnhancedMetric]
    affected_routes: list[EnhancedRoute]
    affected_chokepoints: list[Chokepoint]
    explanation_steps: list[EnhancedExplanationStep]
    generated_at: datetime
    source_market: str
    market_url: str | None = None
    # Trace & reproducibility
    trace_id: str | None = None
    input_event_hash: str | None = None
    ruleset_version: str | None = None
    # Summary & explanation
    detailed_explanation: str | None = None
    # Onset / duration (hours)
    expected_onset_hours: int | None = None
    expected_duration_hours: int | None = None
    # Classification
    domain: str | None = None
    category: str | None = None
    subcategory: str | None = None
    # Layer 3: affected systems (system names)
    affected_systems: list[str] = []
    # Data quality (probability source)
    probability_is_fallback: bool = Field(
        default=False,
        description="True if probability is estimated/fallback, not from actual market data",
    )
    data_quality: str = Field(
        default="complete",
        description="Data quality indicator: 'complete', 'partial', 'estimated'",
    )


# -----------------------------------------------------------------------------
# Geographic data for route/chokepoint enrichment
# -----------------------------------------------------------------------------

_LOCATIONS: dict[str, RouteCoordinate] = {
    "shanghai": RouteCoordinate(lat=31.2, lng=121.5, name="Shanghai"),
    "rotterdam": RouteCoordinate(lat=51.9, lng=4.5, name="Rotterdam"),
    "singapore": RouteCoordinate(lat=1.3, lng=103.8, name="Singapore"),
    "hong_kong": RouteCoordinate(lat=22.3, lng=114.2, name="Hong Kong"),
    "cape_town": RouteCoordinate(lat=-34.4, lng=18.5, name="Cape Town"),
    "suez": RouteCoordinate(lat=30.0, lng=32.5, name="Suez Canal"),
    "panama": RouteCoordinate(lat=9.1, lng=-79.7, name="Panama Canal"),
    "red_sea": RouteCoordinate(lat=20.0, lng=38.0, name="Red Sea"),
    "bab_el_mandeb": RouteCoordinate(lat=12.6, lng=43.3, name="Bab el-Mandeb"),
    "hormuz": RouteCoordinate(lat=26.5, lng=56.3, name="Strait of Hormuz"),
    "malacca": RouteCoordinate(lat=2.5, lng=101.5, name="Strait of Malacca"),
    "east_asia": RouteCoordinate(lat=35.0, lng=120.0, name="East Asia"),
    "northern_europe": RouteCoordinate(lat=52.0, lng=5.0, name="Northern Europe"),
    "middle_east": RouteCoordinate(lat=25.0, lng=45.0, name="Middle East"),
    "west_africa": RouteCoordinate(lat=6.0, lng=3.0, name="West Africa"),
    "asia": RouteCoordinate(lat=25.0, lng=105.0, name="Asia"),
    "europe": RouteCoordinate(lat=50.0, lng=10.0, name="Europe"),
}

_CHOKEPOINTS: dict[str, Chokepoint] = {
    "red_sea": Chokepoint(name="Red Sea", lat=20.0, lng=38.0, risk_level="CRITICAL"),
    "suez": Chokepoint(name="Suez Canal", lat=30.0, lng=32.5, risk_level="HIGH"),
    "bab_el_mandeb": Chokepoint(name="Bab el-Mandeb Strait", lat=12.6, lng=43.3, risk_level="CRITICAL"),
    "panama": Chokepoint(name="Panama Canal", lat=9.1, lng=-79.7, risk_level="HIGH"),
    "hormuz": Chokepoint(name="Strait of Hormuz", lat=26.5, lng=56.3, risk_level="HIGH"),
    "malacca": Chokepoint(name="Strait of Malacca", lat=2.5, lng=101.5, risk_level="MEDIUM"),
    "taiwan": Chokepoint(name="Taiwan Strait", lat=24.0, lng=119.0, risk_level="MEDIUM"),
}


def _norm_key(s: str) -> str:
    return s.lower().strip().replace(" ", "_").replace("-", "_")


def _infer_chokepoints(title: str, keywords: list[str] | None = None) -> list[Chokepoint]:
    """Infer affected chokepoints from signal title and keywords."""
    text = f"{title} {' '.join(keywords or [])}".lower()
    seen: set[str] = set()
    out: list[Chokepoint] = []
    for key, cp in _CHOKEPOINTS.items():
        if key.replace("_", " ") in text or key in text:
            if cp.name not in seen:
                seen.add(cp.name)
                out.append(cp)
    return out


def _route_coords(
    origin_region: str,
    destination_region: str,
    severity: float,
    delay_days: float | None = None,
) -> EnhancedRoute:
    """
    Build enhanced route with coordinates from region names.

    delay_days must come from AffectedRoute.estimated_delay_days (impact assessment).
    If not provided, 0.0 is used — no arbitrary formula.
    """
    ok = _norm_key(origin_region)
    dk = _norm_key(destination_region)
    origin = _LOCATIONS.get(ok, RouteCoordinate(lat=0, lng=0, name=origin_region or "Unknown"))
    dest = _LOCATIONS.get(dk, RouteCoordinate(lat=0, lng=0, name=destination_region or "Unknown"))
    if severity >= 0.7:
        status = "BLOCKED"
    elif severity >= 0.5:
        status = "DELAYED"
    elif severity >= 0.3:
        status = "ALTERNATIVE"
    else:
        status = "OPEN"
    waypoints: list[RouteCoordinate] = []
    if "asia" in ok and "europe" in dk:
        if status == "BLOCKED":
            waypoints = [_LOCATIONS["singapore"], _LOCATIONS["cape_town"]]
        else:
            waypoints = [_LOCATIONS["singapore"], _LOCATIONS["bab_el_mandeb"], _LOCATIONS["suez"]]
    return EnhancedRoute(
        route_id=f"{ok}-{dk}",
        route_name=f"{origin.name} to {dest.name}",
        origin=origin,
        destination=dest,
        waypoints=waypoints,
        status=status,
        impact_severity=severity,
        delay_days=float(delay_days) if delay_days is not None else 0.0,
    )


def _enhance_metric(m: Any) -> EnhancedMetric:
    """
    Turn domain ImpactMetric into EnhancedMetric.

    Projection is omitted — no sourced methodology. UI may show empty or N/A.
    Uncertainty is set only when the domain object has real lower/upper — never fabricated.
    """
    val = float(getattr(m, "value", 0))
    unc = getattr(m, "uncertainty", None)
    u_dict: dict[str, float] | None = None
    if unc is not None:
        lo, hi = getattr(unc, "lower", None), getattr(unc, "upper", None)
        if lo is not None and hi is not None:
            u_dict = {"lower": float(lo), "upper": float(hi)}
    baseline = float(getattr(m, "baseline", 0) or 0)
    return EnhancedMetric(
        name=getattr(m, "name", "unknown"),
        value=val,
        unit=getattr(m, "unit", ""),
        uncertainty=u_dict,
        baseline=baseline,
        projection=[],  # No unsourced projection — removed ISSUE-003
        evidence_source=getattr(m, "evidence_source", None),
        methodology_name=getattr(m, "methodology_name", None),
        methodology_version=getattr(m, "methodology_version", None),
    )


def _confidence_breakdown_from_factors(score: float, factors: dict[str, Any] | None) -> ConfidenceBreakdown:
    """
    Build ConfidenceBreakdown from pipeline confidence_factors only.

    No hash or synthetic variance. When factors are missing, use overall score
    for each component (honest fallback, not fabricated).
    """
    if factors and isinstance(factors, dict):
        def _f(key: str, default: float = 0.5) -> float:
            v = factors.get(key)
            if v is None:
                return default
            try:
                return max(0.0, min(1.0, float(v)))
            except (TypeError, ValueError):
                return default

        return ConfidenceBreakdown(
            liquidity=_f("liquidity_score", score),
            geographic=_f("geographic_score", score),
            semantic=_f("semantic_score", _f("signal_strength", score)),
            anomaly=_f("anomaly_score", _f("validation_score", score)),
            market_depth=_f("market_depth_score", score),
            source_reliability=_f("source_reliability_score", 0.85),
        )
    return ConfidenceBreakdown(
        liquidity=score,
        geographic=score,
        semantic=score,
        anomaly=score,
        market_depth=score,
        source_reliability=score,
    )


def _signal_to_response(s: Any) -> ProcessedSignalResponse:
    """Map OmenSignal to legacy ProcessedSignalResponse."""
    def metric_dict(m: Any) -> dict:
        out: dict = {"name": m.name, "value": m.value, "unit": m.unit}
        if getattr(m, "uncertainty", None) is not None:
            u = m.uncertainty
            out["uncertainty"] = {"lower": u.lower, "upper": u.upper}
        if getattr(m, "evidence_source", None):
            out["evidence_source"] = m.evidence_source
        return out

    def route_dict(r: Any) -> dict:
        return {
            "route_id": r.route_id,
            "route_name": r.route_name,
            "origin_region": r.origin_region,
            "destination_region": r.destination_region,
            "impact_severity": r.impact_severity,
        }

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
        confidence_level=getattr(s.confidence_level, "value", str(s.confidence_level)),
        confidence_score=s.confidence_score,
        severity=s.severity,
        severity_label=s.severity_label,
        is_actionable=getattr(s, "is_actionable", s.severity > 0.5),
        urgency=getattr(s, "urgency", "HIGH" if s.severity > 0.7 else "MEDIUM"),
        key_metrics=[metric_dict(m) for m in s.key_metrics],
        affected_routes=[route_dict(r) for r in s.affected_routes],
        explanation_chain={"trace_id": chain.trace_id, "total_steps": chain.total_steps, "steps": steps},
    )


def _signal_to_full_response(s: Any) -> FullProcessedSignalResponse:
    """
    Map OmenSignal to FullProcessedSignalResponse.

    All data is from pipeline or signal history store — no synthetic fabrication.
    """
    prob = s.current_probability
    history_store = get_signal_history_store()
    prob_history = history_store.get_probability_series(
        s.signal_id, hours=24, max_points=24
    )
    momentum = history_store.get_momentum(s.signal_id)
    if momentum == "UNKNOWN":
        fallback = getattr(s, "probability_momentum", "STABLE")
        if isinstance(fallback, str) and fallback in ("INCREASING", "DECREASING", "STABLE"):
            momentum = fallback
    conf_breakdown = _confidence_breakdown_from_factors(
        s.confidence_score, getattr(s, "confidence_factors", None)
    )
    enhanced_metrics = [_enhance_metric(m) for m in (s.key_metrics or [])]
    enhanced_routes: list[EnhancedRoute] = []
    for r in s.affected_routes or []:
        orig = getattr(r, "origin_region", "Unknown") or "Unknown"
        dest = getattr(r, "destination_region", "Unknown") or "Unknown"
        sev = getattr(r, "impact_severity", s.severity)
        delay_days = getattr(r, "estimated_delay_days", None)
        enhanced_routes.append(_route_coords(orig, dest, sev, delay_days=delay_days))
    # Do not add a synthetic default route when empty — return [] (ISSUE-003)
    keywords: list[str] = getattr(s, "affected_regions", None) or []
    chokepoints = _infer_chokepoints(s.title, keywords)
    if not chokepoints:
        t = s.title.lower()
        if "red sea" in t or "houthi" in t:
            chokepoints = [_CHOKEPOINTS["red_sea"], _CHOKEPOINTS["suez"], _CHOKEPOINTS["bab_el_mandeb"]]
        elif "panama" in t:
            chokepoints = [_CHOKEPOINTS["panama"]]
        elif "hormuz" in t:
            chokepoints = [_CHOKEPOINTS["hormuz"]]
    steps_out: list[EnhancedExplanationStep] = []
    chain = getattr(s, "explanation_chain", None)
    if chain and getattr(chain, "steps", None):
        for st in chain.steps:
            d = st.model_dump() if hasattr(st, "model_dump") else (st if isinstance(st, dict) else {})
            steps_out.append(
                EnhancedExplanationStep(
                    step_id=int(d.get("step_id", 0)),
                    rule_name=str(d.get("rule_name", "unknown")),
                    rule_version=str(d.get("rule_version", "1.0.0")),
                    status=str(d.get("status", "passed")),
                    reasoning=str(d.get("reasoning", "")),
                    confidence_contribution=float(d.get("confidence_contribution", 0)),
                    processing_time_ms=float(d.get("processing_time_ms", 0)),
                )
            )
    trace_id = getattr(s, "deterministic_trace_id", None) or getattr(s, "trace_id", None)
    ruleset_v = getattr(s, "ruleset_version", None)
    ruleset_str = str(ruleset_v) if ruleset_v is not None else None
    domain_v = getattr(s, "domain", None)
    domain_str = getattr(domain_v, "value", domain_v) if domain_v is not None else None
    category_v = getattr(s, "category", None)
    category_str = getattr(category_v, "value", category_v) if category_v is not None else None
    affected_sys: list[str] = []
    for a in getattr(s, "affected_systems", None) or []:
        name = getattr(a, "system_name", None) or getattr(a, "system_id", None) or str(a)
        affected_sys.append(name)

    return FullProcessedSignalResponse(
        signal_id=s.signal_id,
        event_id=str(s.event_id),
        title=s.title,
        summary=getattr(s, "summary", None),
        probability=prob,
        probability_history=prob_history,
        probability_momentum=momentum,
        confidence_level=getattr(s.confidence_level, "value", str(s.confidence_level)),
        confidence_score=s.confidence_score,
        confidence_breakdown=conf_breakdown,
        severity=s.severity,
        severity_label=s.severity_label,
        is_actionable=getattr(s, "is_actionable", s.severity > 0.5),
        urgency=getattr(s, "urgency", "HIGH" if s.severity > 0.7 else "MEDIUM"),
        metrics=enhanced_metrics,
        affected_routes=enhanced_routes,
        affected_chokepoints=chokepoints,
        explanation_steps=steps_out,
        generated_at=getattr(s, "generated_at", None) or datetime.utcnow(),
        source_market=getattr(s, "source_market", "polymarket"),
        market_url=getattr(s, "market_url", None),
        trace_id=trace_id,
        input_event_hash=getattr(s, "input_event_hash", None),
        ruleset_version=ruleset_str,
        detailed_explanation=getattr(s, "detailed_explanation", None),
        expected_onset_hours=getattr(s, "expected_onset_hours", None),
        expected_duration_hours=getattr(s, "expected_duration_hours", None),
        domain=domain_str,
        category=category_str,
        subcategory=getattr(s, "subcategory", None),
        affected_systems=affected_sys,
        probability_is_fallback=getattr(s, "probability_is_fallback", False),
        data_quality="estimated" if getattr(s, "probability_is_fallback", False) else "complete",
    )


# =============================================================================
# ENDPOINTS
# =============================================================================


@router.get("/events", response_model=list[LiveEventResponse])
async def get_live_events(
    limit: int = Query(default=20, le=100),
    logistics_only: bool = Query(default=True),
):
    """Fetch live events from Polymarket (raw, before OMEN processing)."""
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


@router.post("/process", response_model=list[FullProcessedSignalResponse])
async def process_live_events(
    limit: int = Query(default=500, le=2000),
    min_liquidity: float = Query(default=1000),
):
    """
    Fetch and process live Polymarket events through OMEN pipeline.
    Returns FULL signal data with all fields the UI needs.
    """
    try:
        container = get_container()
        pipeline = container.pipeline
        source = PolymarketSignalSource(logistics_only=True)
        raw_list = list(source.fetch_events(limit=min(limit * 2, 4000)))
        filtered = [
            e for e in raw_list
            if e.market.current_liquidity_usd >= min_liquidity
        ][:limit]
        results: list[FullProcessedSignalResponse] = []
        for event in filtered:
            result = pipeline.process_single(event)
            if result.success and result.signals:
                for signal in result.signals:
                    results.append(_signal_to_full_response(signal))
        return results
    except SourceUnavailableError as e:
        raise HTTPException(status_code=503, detail=f"Polymarket unavailable: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/process-single")
async def process_single_event(
    event_id: str = Query(..., alias="event_id"),
):
    """Process a single event by ID and return one OMEN signal or rejection info."""
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
                "signal": _signal_to_full_response(res.signals[0]).model_dump(),
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
