"""Middleware for OMEN API."""

from omen.infrastructure.middleware.request_tracking import (
    RequestTrackingMiddleware,
    clear_shutdown,
    get_active_request_count,
    is_shutting_down,
    request_tracking_middleware,
    set_shutdown,
    wait_for_requests_to_drain,
)

__all__ = [
    "RequestTrackingMiddleware",
    "clear_shutdown",
    "get_active_request_count",
    "is_shutting_down",
    "request_tracking_middleware",
    "set_shutdown",
    "wait_for_requests_to_drain",
]
