"""
Trace Context Middleware

Extracts or generates trace context for each request.
Supports W3C Trace Context, X-Request-ID, and custom headers.
"""

import logging
import uuid
from typing import Callable

from starlette.requests import Request
from starlette.responses import Response

from omen.infrastructure.observability.logging import (
    clear_trace_context,
    set_trace_context,
)

logger = logging.getLogger(__name__)

TRACE_HEADERS = [
    "traceparent",
    "x-trace-id",
    "x-request-id",
    "x-correlation-id",
]


def _parse_trace_id(value: str) -> str:
    """Parse trace ID from various formats."""
    if "-" in value and len(value) > 32:
        parts = value.split("-")
        if len(parts) >= 2:
            return parts[1][:16]
    return value[:16] if len(value) > 16 else value


def _extract_trace_id(request: Request) -> str:
    """Extract trace ID from headers or generate new one."""
    for header in TRACE_HEADERS:
        value = request.headers.get(header)
        if value:
            return _parse_trace_id(value)
    return uuid.uuid4().hex[:16]


async def trace_context_middleware(
    request: Request, call_next: Callable[[Request], Response]
) -> Response:
    """
    Inject trace context into every request.

    Supported headers (in priority order):
    1. traceparent (W3C Trace Context)
    2. x-trace-id (Custom)
    3. x-request-id (Common)
    4. x-correlation-id (AWS)
    """
    trace_id = _extract_trace_id(request)
    request_id = uuid.uuid4().hex[:8]

    # Set on request.state for error handlers and downstream use
    request.state.trace_id = trace_id
    request.state.request_id = request_id

    set_trace_context(trace_id=trace_id, request_id=request_id)
    logger.info(
        "%s %s",
        request.method,
        request.url.path,
        extra={
            "event": "request_start",
            "method": request.method,
            "path": request.url.path,
            "query": str(request.query_params) if request.query_params else None,
        },
    )
    try:
        response = await call_next(request)
        logger.info(
            "%s %s -> %s",
            request.method,
            request.url.path,
            response.status_code,
            extra={
                "event": "request_end",
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
            },
        )
        if hasattr(response, "headers"):
            response.headers["x-trace-id"] = trace_id
            response.headers["x-request-id"] = request_id
        return response
    except Exception as e:
        logger.error(
            "Request failed: %s",
            e,
            extra={
                "event": "request_error",
                "method": request.method,
                "path": request.url.path,
            },
            exc_info=True,
        )
        raise
    finally:
        clear_trace_context()
