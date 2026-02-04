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
from omen.infrastructure.middleware.live_gate_middleware import (
    LiveGateMiddleware,
    get_omen_mode,
    get_gate_result,
)
from omen.infrastructure.middleware.response_wrapper import (
    ResponseWrapperMiddleware,
)

__all__ = [
    # Request tracking
    "RequestTrackingMiddleware",
    "clear_shutdown",
    "get_active_request_count",
    "is_shutting_down",
    "request_tracking_middleware",
    "set_shutdown",
    "wait_for_requests_to_drain",
    # Live gate
    "LiveGateMiddleware",
    "get_omen_mode",
    "get_gate_result",
    # Response wrapper
    "ResponseWrapperMiddleware",
]
