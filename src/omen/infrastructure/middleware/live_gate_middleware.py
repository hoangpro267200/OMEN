"""
LIVE Gate Middleware - Layer 3 Request-Level Enforcement.

This middleware intercepts every API request and:
1. Extracts the requested mode (from header or query param)
2. Calls LiveGateService to validate the request
3. Injects the granted mode into request.state
4. Adds mode headers to the response

If LIVE mode is requested but blocked:
- Option A: Return 403 Forbidden
- Option B: Downgrade to DEMO and continue (current implementation)

We use Option B for better UX - users can still access data in DEMO mode.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Callable, Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse

from omen.application.services.live_gate_service import (
    LiveGateService,
    GateCheckResult,
    get_live_gate_service,
)

logger = logging.getLogger(__name__)


class LiveGateMiddleware(BaseHTTPMiddleware):
    """
    Middleware for LIVE mode gate enforcement.

    Layer 3 of the 3-layer enforcement system:
    - Intercepts all requests
    - Validates mode requests against gate status
    - Injects granted mode into request state
    - Adds mode headers to responses

    Usage:
        app.add_middleware(LiveGateMiddleware)

        # Or with custom service
        app.add_middleware(LiveGateMiddleware, gate_service=my_service)
    """

    def __init__(
        self,
        app,
        gate_service: Optional[LiveGateService] = None,
        strict_mode: bool = False,
        excluded_paths: Optional[list[str]] = None,
    ):
        """
        Initialize LiveGateMiddleware.

        Args:
            app: FastAPI/Starlette application
            gate_service: LiveGateService instance (defaults to global)
            strict_mode: If True, return 403 for blocked LIVE requests.
                        If False, downgrade to DEMO (default).
            excluded_paths: Paths to exclude from gate check (e.g., /health)
        """
        super().__init__(app)
        self._gate_service = gate_service or get_live_gate_service()
        self._strict_mode = strict_mode
        self._excluded_paths = excluded_paths or [
            "/health",
            "/ready",
            "/metrics",
            "/docs",
            "/openapi.json",
            "/redoc",
        ]

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        """
        Process request through the gate.

        1. Extract requested mode from headers/query
        2. Check gate status
        3. Set request.state.omen_mode
        4. Process request
        5. Add response headers
        """
        # Skip gate check for excluded paths
        if self._is_excluded_path(request.url.path):
            response = await call_next(request)
            return response

        # Extract requested mode
        requested_mode = self._extract_requested_mode(request)

        # Check gate
        gate_result = self._gate_service.check_gate(requested_mode)

        # Handle blocked LIVE requests
        if requested_mode == "LIVE" and gate_result.is_blocked:
            if self._strict_mode:
                return self._create_blocked_response(gate_result)
            else:
                # Log the downgrade
                logger.info(
                    "LIVE mode requested but blocked, downgrading to DEMO: %s",
                    [r.value for r in gate_result.block_reasons],
                )

        # Inject into request state
        request.state.omen_mode = gate_result.granted_mode
        request.state.omen_gate_result = gate_result
        request.state.omen_requested_mode = requested_mode

        # Process request
        response = await call_next(request)

        # Add response headers
        response = self._add_response_headers(response, gate_result)

        return response

    def _is_excluded_path(self, path: str) -> bool:
        """Check if path is excluded from gate check."""
        for excluded in self._excluded_paths:
            if path.startswith(excluded):
                return True
        return False

    def _extract_requested_mode(self, request: Request) -> str:
        """
        Extract requested mode from request.

        Priority:
        1. X-OMEN-Mode header
        2. ?mode= query parameter
        3. Default to DEMO
        """
        # Check header first
        header_mode = request.headers.get("X-OMEN-Mode", "").upper()
        if header_mode in ("LIVE", "DEMO"):
            return header_mode

        # Check query parameter
        query_mode = request.query_params.get("mode", "").upper()
        if query_mode in ("LIVE", "DEMO"):
            return query_mode

        # Default to DEMO
        return "DEMO"

    def _add_response_headers(
        self,
        response: Response,
        gate_result: GateCheckResult,
    ) -> Response:
        """Add OMEN mode headers to response."""
        response.headers["X-OMEN-Mode"] = gate_result.granted_mode
        response.headers["X-OMEN-Real-Coverage"] = str(
            round(gate_result.real_source_ratio, 3)
        )
        response.headers["X-OMEN-Gate-Status"] = gate_result.decision.value

        if gate_result.granted_mode == "DEMO":
            response.headers["X-OMEN-Disclaimer"] = (
                "Contains simulated data. Not for trading decisions."
            )

        return response

    def _create_blocked_response(self, gate_result: GateCheckResult) -> JSONResponse:
        """Create 403 response for blocked LIVE mode requests."""
        return JSONResponse(
            status_code=403,
            content={
                "error": "LIVE_MODE_BLOCKED",
                "message": gate_result.get_user_message(),
                "details": {
                    "requested_mode": gate_result.requested_mode,
                    "granted_mode": gate_result.granted_mode,
                    "block_reasons": [r.value for r in gate_result.block_reasons],
                    "real_source_coverage": round(gate_result.real_source_ratio, 3),
                    "required_coverage": gate_result.required_ratio,
                    "mock_sources": gate_result.mock_sources,
                },
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            headers={
                "X-OMEN-Mode": "DEMO",
                "X-OMEN-Real-Coverage": str(round(gate_result.real_source_ratio, 3)),
                "X-OMEN-Gate-Status": "BLOCKED",
            },
        )


def get_omen_mode(request: Request) -> str:
    """
    Get the granted OMEN mode from request state.

    Use this in route handlers to get the current mode.

    Usage:
        @router.get("/signals")
        async def get_signals(request: Request):
            mode = get_omen_mode(request)
            # Query from demo.* or live.* based on mode
    """
    return getattr(request.state, "omen_mode", "DEMO")


def get_gate_result(request: Request) -> Optional[GateCheckResult]:
    """
    Get the full gate check result from request state.

    Use this for detailed gate information in responses.
    """
    return getattr(request.state, "omen_gate_result", None)
