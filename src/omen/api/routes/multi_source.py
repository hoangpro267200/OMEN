"""
Multi-source API endpoints.

Provides unified access to all signal sources (Polymarket, AIS, Weather, Freight).
"""

from typing import Literal
from fastapi import APIRouter, Query, Depends
from pydantic import BaseModel, Field
from datetime import datetime

from omen.api.errors import not_found, bad_request
from omen.infrastructure.security.auth import verify_api_key
from omen.adapters.inbound.multi_source import get_multi_source_aggregator

router = APIRouter()


class SourceInfo(BaseModel):
    """Information about a signal source."""

    name: str
    enabled: bool
    priority: int
    weight: float
    status: str = "unknown"


class SourceHealthResponse(BaseModel):
    """Health status of all sources."""

    sources: list[SourceInfo]
    healthy_count: int
    total_count: int


class MultiSourceSignal(BaseModel):
    """Signal from multi-source aggregation."""

    event_id: str
    source: str
    title: str
    description: str
    probability: float
    keywords: list[str]
    locations: list[str]
    timestamp: str
    source_metrics: dict | None = None


class MultiSourceResponse(BaseModel):
    """Response from multi-source fetch."""

    signals: list[MultiSourceSignal]
    total: int
    by_source: dict[str, int]
    fetch_time_ms: float


@router.get("/sources", response_model=SourceHealthResponse)
async def list_sources() -> SourceHealthResponse:
    """
    List all registered signal sources and their status.

    Returns health status of each source:
    - Polymarket: Prediction market data
    - AIS: Ship tracking, port congestion
    - Weather: Storm alerts, sea conditions
    - Freight: Container rates, capacity
    """
    aggregator = get_multi_source_aggregator()
    sources = aggregator.list_sources()
    health = aggregator.get_source_health()

    source_infos = []
    healthy_count = 0

    for s in sources:
        status = health.get(s["name"], {}).get("status", "unknown")
        if status == "healthy":
            healthy_count += 1

        source_infos.append(
            SourceInfo(
                name=s["name"],
                enabled=s["enabled"],
                priority=s["priority"],
                weight=s["weight"],
                status=status,
            )
        )

    return SourceHealthResponse(
        sources=source_infos,
        healthy_count=healthy_count,
        total_count=len(sources),
    )


@router.get("/signals", response_model=MultiSourceResponse)
async def get_multi_source_signals(
    limit_per_source: int = Query(default=20, le=100),
    sources: str | None = Query(
        default=None,
        description="Comma-separated source names (e.g., 'ais,weather,freight')",
    ),
    _api_key: str = Depends(verify_api_key),
) -> MultiSourceResponse:
    """
    Get signals from multiple sources.

    Sources:
    - polymarket: Prediction market signals
    - ais: Port congestion, chokepoint delays
    - weather: Storm alerts, sea conditions
    - freight: Rate spikes, capacity alerts

    Signals are combined and sorted by timestamp.
    """
    import time

    start_time = time.perf_counter()

    aggregator = get_multi_source_aggregator()

    # Parse source filter
    source_filter = None
    if sources:
        source_filter = [s.strip() for s in sources.split(",")]

    # Fetch from all sources
    events = aggregator.fetch_all(
        limit_per_source=limit_per_source,
        sources=source_filter,
    )

    # Convert to response format
    signals = []
    by_source: dict[str, int] = {}

    for event in events:
        source = event.market.source
        by_source[source] = by_source.get(source, 0) + 1

        signals.append(
            MultiSourceSignal(
                event_id=event.event_id,
                source=source,
                title=event.title,
                description=event.description[:500] if event.description else "",
                probability=event.probability,
                keywords=event.keywords[:10] if event.keywords else [],
                locations=[loc.name for loc in event.inferred_locations[:5] if loc.name] if event.inferred_locations else [],
                timestamp=event.observed_at.isoformat() if event.observed_at else "",
                source_metrics=getattr(event, "source_metrics", {}),
            )
        )

    fetch_time = (time.perf_counter() - start_time) * 1000

    return MultiSourceResponse(
        signals=signals,
        total=len(signals),
        by_source=by_source,
        fetch_time_ms=round(fetch_time, 1),
    )


class SourceUpdateRequest(BaseModel):
    """Request to update a source's configuration."""

    enabled: bool = Field(..., description="Enable or disable the source")


@router.patch("/sources/{source_name}")
async def update_source(
    source_name: str,
    request: SourceUpdateRequest,
    _api_key: str = Depends(verify_api_key),
) -> dict[str, str]:
    """
    Update a signal source configuration.

    Set enabled=true to enable, enabled=false to disable.
    """
    aggregator = get_multi_source_aggregator()

    sources = {s["name"] for s in aggregator.list_sources()}
    if source_name not in sources:
        raise not_found("Source", source_name)

    if request.enabled:
        aggregator.enable_source(source_name)
        return {"status": "enabled", "source": source_name}
    else:
        aggregator.disable_source(source_name)
        return {"status": "disabled", "source": source_name}


@router.get("/sources/{source_name}/signals", response_model=MultiSourceResponse)
async def get_single_source_signals(
    source_name: str,
    limit: int = Query(default=50, le=200),
    _api_key: str = Depends(verify_api_key),
) -> MultiSourceResponse:
    """Get signals from a specific source."""
    import time

    start_time = time.perf_counter()

    aggregator = get_multi_source_aggregator()

    sources = {s["name"] for s in aggregator.list_sources()}
    if source_name not in sources:
        raise not_found("Source", source_name)

    try:
        events = aggregator.fetch_by_source(source_name, limit=limit)
    except ValueError as e:
        raise bad_request(str(e))

    signals = []
    for event in events:
        signals.append(
            MultiSourceSignal(
                event_id=event.event_id,
                source=event.market.source,
                title=event.title,
                description=event.description[:500] if event.description else "",
                probability=event.probability,
                keywords=event.keywords[:10] if event.keywords else [],
                locations=[loc.name for loc in event.inferred_locations[:5] if loc.name] if event.inferred_locations else [],
                timestamp=event.observed_at.isoformat() if event.observed_at else "",
                source_metrics=event.source_metrics,
            )
        )

    fetch_time = (time.perf_counter() - start_time) * 1000

    return MultiSourceResponse(
        signals=signals,
        total=len(signals),
        by_source={source_name: len(signals)},
        fetch_time_ms=round(fetch_time, 1),
    )
