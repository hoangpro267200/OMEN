"""
HTTP Request Metrics Middleware.

Tracks request latency (p50, p95, p99), request/response sizes, and request counts.
"""

import time
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from omen.infrastructure.observability.metrics import (
    HTTP_REQUEST_DURATION,
    HTTP_REQUESTS_TOTAL,
    HTTP_REQUESTS_IN_PROGRESS,
    HTTP_REQUEST_SIZE_BYTES,
    HTTP_RESPONSE_SIZE_BYTES,
)


def _normalize_endpoint(path: str) -> str:
    """
    Normalize endpoint path to reduce cardinality.
    
    Replaces dynamic path parameters with placeholders:
    - /api/v1/signals/abc123 -> /api/v1/signals/{id}
    - /health/sources/polymarket -> /health/sources/{source}
    """
    parts = path.split("/")
    normalized = []
    
    for i, part in enumerate(parts):
        if not part:
            normalized.append(part)
            continue
            
        # Check if this looks like a dynamic ID
        # (UUID, hex string, or alphanumeric longer than 10 chars)
        if (
            len(part) > 10 and part.isalnum()
        ) or (
            len(part) == 36 and "-" in part  # UUID
        ) or (
            len(part) >= 12 and all(c in "0123456789abcdefABCDEF-" for c in part)  # Hex/ID
        ):
            # Use context-aware placeholder
            if i > 0:
                prev = normalized[-1] if normalized else ""
                if prev == "signals":
                    normalized.append("{signal_id}")
                elif prev == "sources":
                    normalized.append("{source}")
                elif prev == "partitions":
                    normalized.append("{partition}")
                elif prev == "partner-signals":
                    normalized.append("{symbol}")
                else:
                    normalized.append("{id}")
            else:
                normalized.append("{id}")
        else:
            normalized.append(part)
    
    return "/".join(normalized)


async def http_metrics_middleware(request: Request, call_next: Callable) -> Response:
    """
    Middleware to track HTTP request metrics.
    
    Tracks:
    - Request duration (histogram for p50, p95, p99)
    - Request count by status code
    - Requests in progress
    - Request/response body sizes
    """
    method = request.method
    endpoint = _normalize_endpoint(request.url.path)
    
    # Skip metrics endpoint to avoid recursion
    if endpoint == "/metrics":
        return await call_next(request)
    
    # Track in-progress requests
    HTTP_REQUESTS_IN_PROGRESS.labels(method=method, endpoint=endpoint).inc()
    
    # Track request size
    content_length = request.headers.get("content-length")
    if content_length:
        try:
            HTTP_REQUEST_SIZE_BYTES.labels(
                method=method, endpoint=endpoint
            ).observe(int(content_length))
        except ValueError:
            pass
    
    # Time the request
    start_time = time.perf_counter()
    status_code = "500"  # Default in case of exception
    response_size = 0
    
    try:
        response = await call_next(request)
        status_code = str(response.status_code)
        
        # Track response size
        response_size_header = response.headers.get("content-length")
        if response_size_header:
            try:
                response_size = int(response_size_header)
            except ValueError:
                pass
        
        return response
    except Exception:
        status_code = "500"
        raise
    finally:
        # Record duration
        duration = time.perf_counter() - start_time
        HTTP_REQUEST_DURATION.labels(
            method=method, endpoint=endpoint, status_code=status_code
        ).observe(duration)
        
        # Record request count
        HTTP_REQUESTS_TOTAL.labels(
            method=method, endpoint=endpoint, status_code=status_code
        ).inc()
        
        # Record response size
        if response_size > 0:
            HTTP_RESPONSE_SIZE_BYTES.labels(
                method=method, endpoint=endpoint, status_code=status_code
            ).observe(response_size)
        
        # Decrement in-progress
        HTTP_REQUESTS_IN_PROGRESS.labels(method=method, endpoint=endpoint).dec()


class HTTPMetricsMiddleware(BaseHTTPMiddleware):
    """Starlette-compatible middleware wrapper."""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        return await http_metrics_middleware(request, call_next)
