"""Prometheus metrics endpoint."""

from fastapi import APIRouter, Depends, Response

from omen.api.route_dependencies import require_stats_read
from omen.infrastructure.observability.metrics import (
    get_metrics,
    get_metrics_content_type,
)
from omen.infrastructure.security.unified_auth import AuthContext

router = APIRouter(tags=["metrics"])


@router.get("/metrics")
async def metrics_endpoint(
    auth: AuthContext = Depends(require_stats_read),  # RBAC: read:stats
) -> Response:
    """
    Prometheus metrics endpoint.

    Returns metrics in Prometheus text format.
    Scrape this endpoint with Prometheus.
    """
    return Response(
        content=get_metrics(),
        media_type=get_metrics_content_type(),
    )
