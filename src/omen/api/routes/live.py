"""
Live Polymarket data endpoints for demo UI.

Fetches from Gamma API, runs OMEN pipeline, returns results for the React app.
All data in responses is traceable to pipeline or storage — no synthetic fabrication.

Signal-only contract: endpoints return SignalResponse only. No impact-shaped types.

Security: Requires WRITE_SIGNALS scope for processing operations.
"""

from typing import Any

from fastapi import APIRouter, Depends, Query

from omen.application.container import get_container
from omen.domain.errors import SourceUnavailableError
from omen.adapters.inbound.polymarket.source import PolymarketSignalSource
from omen.api.models.responses import SignalResponse
from omen.api.errors import not_found, service_unavailable, internal_error
from omen.infrastructure.security.auth import verify_api_key
from omen.infrastructure.security.rbac import Scopes, require_scopes

router = APIRouter(prefix="/live", tags=["Live Data"])

# Security dependencies for live processing routes
_write_deps = [Depends(verify_api_key), Depends(require_scopes([Scopes.WRITE_SIGNALS]))]


# =============================================================================
# ENDPOINTS (pure signal contract only; no raw data exposure)
# =============================================================================
# Raw data endpoints (GET /events, GET /events/search) removed — V7 compliance.
# Use SignalResponse from omen.api.models.responses for process endpoints.


@router.post(
    "/signals",
    response_model=list[SignalResponse],
    summary="Process market events into signals",
    description="""
    Transforms market events into structured intelligence signals.

    Output contains probability, confidence, and context only.
    Output does NOT contain impact assessment or decision steering.

    Downstream consumers (e.g. RiskCast) are responsible for:
    - Impact severity calculation
    - Time-horizon or relevance determination
    - High-confidence or relevance assessment
    - Risk quantification
    
    **Requires scope:** `write:signals`
    """,
    dependencies=_write_deps,
)
async def process_live_events(
    limit: int = Query(default=500, le=2000),
    min_liquidity: float = Query(default=1000),
) -> list[SignalResponse]:
    """Fetch and process events through OMEN pipeline. Returns pure signal contract only."""
    try:
        container = get_container()
        pipeline = container.pipeline
        source = PolymarketSignalSource(logistics_only=True)
        raw_list = list(source.fetch_events(limit=min(limit * 2, 4000)))
        filtered = [e for e in raw_list if e.market.current_liquidity_usd >= min_liquidity][:limit]
        out: list[SignalResponse] = []
        for event in filtered:
            result = pipeline.process_single(event)
            if result.success and result.signals:
                for s in result.signals:
                    out.append(SignalResponse.from_domain(s))
        return out
    except SourceUnavailableError as e:
        raise service_unavailable("Polymarket", f"Polymarket unavailable: {e}")
    except Exception as e:
        raise internal_error(str(e), include_trace=True)


@router.post("/signals/{event_id}", dependencies=_write_deps)
async def process_single_event(
    event_id: str,
) -> dict[str, Any]:
    """
    Process a single event by ID. Returns pure signal or rejection reason.

    **Requires scope:** `write:signals`
    """
    try:
        source = PolymarketSignalSource(logistics_only=False)
        container = get_container()
        pipeline = container.pipeline
        event = source.fetch_by_id(event_id)
        if event is None:
            raise not_found("Event", event_id)
        res = pipeline.process_single(event)
        if res.success and res.signals:
            return {
                "signal": SignalResponse.from_domain(res.signals[0]).model_dump(),
                "stats": (
                    {
                        "events_received": res.stats.events_received,
                        "events_validated": res.stats.events_validated,
                        "signals_generated": res.stats.signals_generated,
                    }
                    if res.stats
                    else None
                ),
            }
        return {
            "signal": None,
            "rejection_reason": (
                res.validation_failures[0].reason
                if res.validation_failures
                else "No applicable rules"
            ),
        }
    except SourceUnavailableError as e:
        raise service_unavailable("Polymarket", str(e))
    except Exception as e:
        raise internal_error(str(e), include_trace=True)
