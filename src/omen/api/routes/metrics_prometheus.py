"""Prometheus metrics endpoint."""

from fastapi import APIRouter, Response

from omen.infrastructure.observability.metrics import (
    get_metrics,
    get_metrics_content_type,
)

router = APIRouter(tags=["metrics"])


@router.get("/metrics")
async def metrics_endpoint() -> Response:
    """
    Prometheus metrics endpoint.

    Returns metrics in Prometheus text format.
    Scrape this endpoint with Prometheus.
    """
    return Response(
        content=get_metrics(),
        media_type=get_metrics_content_type(),
    )
