"""
Middleware to track active requests for graceful shutdown.
"""

import asyncio
import logging
from typing import Callable

from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)

# Global counter for active requests
_request_counter = 0
_request_lock: asyncio.Lock | None = None

# Shutdown state (set when graceful shutdown starts)
_shutdown_event: asyncio.Event | None = None


def _get_shutdown_event() -> asyncio.Event:
    global _shutdown_event
    if _shutdown_event is None:
        _shutdown_event = asyncio.Event()
    return _shutdown_event


def set_shutdown() -> None:
    """Mark that graceful shutdown has started (e.g. SIGTERM received)."""
    _get_shutdown_event().set()


def is_shutting_down() -> bool:
    """Return True if shutdown is in progress."""
    return _get_shutdown_event().is_set()


def clear_shutdown() -> None:
    """Clear shutdown state (for tests only)."""
    _get_shutdown_event().clear()


def _get_lock() -> asyncio.Lock:
    global _request_lock
    if _request_lock is None:
        _request_lock = asyncio.Lock()
    return _request_lock


async def request_tracking_middleware(
    request: Request, call_next: Callable[[Request], Response]
) -> Response:
    """Increment/decrement active request count around each request."""
    global _request_counter
    lock = _get_lock()
    async with lock:
        _request_counter += 1
    try:
        response = await call_next(request)
        return response
    finally:
        async with lock:
            _request_counter -= 1


def get_active_request_count() -> int:
    """Return current number of active requests."""
    return _request_counter


async def wait_for_requests_to_drain(timeout: float = 30.0) -> bool:
    """
    Wait until all active requests complete.

    Returns:
        True if drained successfully, False if timeout.
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return True
    start = loop.time()
    while get_active_request_count() > 0:
        elapsed = loop.time() - start
        if elapsed > timeout:
            logger.warning(
                "Drain timeout: %s requests still active",
                get_active_request_count(),
            )
            return False
        await asyncio.sleep(0.1)
    return True


class RequestTrackingMiddleware:
    """
    Track active requests for graceful shutdown.

    Use as: app.middleware("http")(request_tracking_middleware)
    or wrap: RequestTrackingMiddleware wraps the middleware function.
    """

    def __init__(self, app: object):
        self.app = app

    async def __call__(self, scope: dict, receive: Callable, send: Callable) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        global _request_counter
        lock = _get_lock()
        async with lock:
            _request_counter += 1
        try:
            await self.app(scope, receive, send)
        finally:
            async with lock:
                _request_counter -= 1
