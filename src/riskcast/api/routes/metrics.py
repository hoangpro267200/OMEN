"""RiskCast Prometheus /metrics endpoint."""

from fastapi import Response
from fastapi.responses import PlainTextResponse

try:
    from prometheus_client import REGISTRY, generate_latest, CONTENT_TYPE_LATEST

    _metrics_available = True
except ImportError:
    _metrics_available = False


async def metrics() -> Response:
    """Prometheus metrics (empty placeholder if prometheus_client not used)."""
    if _metrics_available:
        return Response(
            content=generate_latest(REGISTRY),
            media_type=CONTENT_TYPE_LATEST,
        )
    return PlainTextResponse("# RiskCast metrics (placeholder)\n", media_type="text/plain")
