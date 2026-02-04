"""
Response Wrapper Middleware.

Wraps all JSON API responses with metadata envelope:
{
    "data": <original_response>,
    "meta": {
        "mode": "DEMO",
        "real_source_coverage": 0.286,
        "live_gate_status": "BLOCKED",
        "mock_sources": ["weather", "stock", ...],
        "real_sources": ["polymarket", "news"],
        "disclaimer": "Contains simulated data.",
        "timestamp": "2026-02-03T12:00:00Z",
        "request_id": "abc123"
    }
}

This ensures every API consumer knows:
- What mode the data is in (DEMO/LIVE)
- What sources are real vs mock
- Whether they should trust the data for decisions
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Optional, Any
from uuid import uuid4

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response, StreamingResponse

from omen.application.services.live_gate_service import GateCheckResult
from omen.infrastructure.data_integrity.source_registry import get_source_registry, SourceType

logger = logging.getLogger(__name__)


class ResponseWrapperMiddleware(BaseHTTPMiddleware):
    """
    Middleware that wraps JSON responses with metadata envelope.

    Features:
    - Adds mode and coverage metadata to all JSON responses
    - Includes disclaimer for DEMO mode
    - Preserves original response for non-JSON content
    - Handles streaming responses gracefully

    Usage:
        app.add_middleware(ResponseWrapperMiddleware)
    """

    def __init__(
        self,
        app,
        excluded_paths: Optional[list[str]] = None,
        include_sources: bool = True,
    ):
        """
        Initialize ResponseWrapperMiddleware.

        Args:
            app: FastAPI/Starlette application
            excluded_paths: Paths to exclude from wrapping (e.g., /health)
            include_sources: Include mock/real source lists in meta
        """
        super().__init__(app)
        self._excluded_paths = excluded_paths or [
            "/health",
            "/ready",
            "/metrics",
            "/docs",
            "/openapi.json",
            "/redoc",
            "/ws",  # WebSocket
        ]
        self._include_sources = include_sources

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        """Process request and wrap JSON response."""
        # Generate request ID
        request_id = str(uuid4())[:8]
        request.state.request_id = request_id

        # Skip wrapping for excluded paths
        if self._is_excluded_path(request.url.path):
            return await call_next(request)

        # Process request
        response = await call_next(request)

        # Only wrap JSON responses
        content_type = response.headers.get("content-type", "")
        if not content_type.startswith("application/json"):
            return response

        # Handle streaming responses
        if isinstance(response, StreamingResponse):
            return await self._wrap_streaming_response(request, response, request_id)

        # Read and wrap response body
        return await self._wrap_response(request, response, request_id)

    def _is_excluded_path(self, path: str) -> bool:
        """Check if path is excluded from wrapping."""
        for excluded in self._excluded_paths:
            if path.startswith(excluded):
                return True
        return False

    async def _wrap_response(
        self,
        request: Request,
        response: Response,
        request_id: str,
    ) -> Response:
        """Wrap a regular response."""
        try:
            # Read response body
            body = b""
            async for chunk in response.body_iterator:
                body += chunk

            # Parse JSON
            original_data = json.loads(body)

            # Check if already wrapped (avoid double-wrapping)
            if isinstance(original_data, dict) and "meta" in original_data and "data" in original_data:
                # Already wrapped, just return
                return Response(
                    content=body,
                    status_code=response.status_code,
                    headers=dict(response.headers),
                    media_type="application/json",
                )

            # Build wrapped response
            wrapped = {
                "data": original_data,
                "meta": self._build_meta(request, request_id),
            }

            # Return new response
            new_body = json.dumps(wrapped, default=str)
            return Response(
                content=new_body,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type="application/json",
            )

        except json.JSONDecodeError:
            # Not valid JSON, return original
            logger.warning("Response body is not valid JSON, skipping wrap")
            return response
        except Exception as e:
            logger.error("Error wrapping response: %s", e)
            return response

    async def _wrap_streaming_response(
        self,
        request: Request,
        response: StreamingResponse,
        request_id: str,
    ) -> Response:
        """Wrap a streaming response (reads full body first)."""
        try:
            # Collect all chunks
            body = b""
            async for chunk in response.body_iterator:
                body += chunk

            # Parse and wrap
            original_data = json.loads(body)

            if isinstance(original_data, dict) and "meta" in original_data and "data" in original_data:
                return Response(
                    content=body,
                    status_code=response.status_code,
                    headers=dict(response.headers),
                    media_type="application/json",
                )

            wrapped = {
                "data": original_data,
                "meta": self._build_meta(request, request_id),
            }

            new_body = json.dumps(wrapped, default=str)
            return Response(
                content=new_body,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type="application/json",
            )

        except Exception as e:
            logger.error("Error wrapping streaming response: %s", e)
            # Return collected body as-is
            return Response(
                content=body,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type="application/json",
            )

    def _build_meta(self, request: Request, request_id: str) -> dict:
        """Build metadata for response envelope."""
        # Get mode from request state (set by LiveGateMiddleware)
        mode = getattr(request.state, "omen_mode", "DEMO")
        gate_result: Optional[GateCheckResult] = getattr(
            request.state, "omen_gate_result", None
        )

        # Build meta
        meta = {
            "mode": mode,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "request_id": request_id,
        }

        # Add gate result info if available
        if gate_result:
            meta["real_source_coverage"] = round(gate_result.real_source_ratio, 3)
            meta["live_gate_status"] = gate_result.decision.value

            if self._include_sources:
                meta["mock_sources"] = gate_result.mock_sources
                meta["real_sources"] = gate_result.real_sources
        else:
            # Fallback to source registry
            registry = get_source_registry()
            sources = registry.get_all_sources()
            real_sources = [s for s in sources if s.source_type == SourceType.REAL]
            mock_sources = [s for s in sources if s.source_type == SourceType.MOCK]

            total = len(sources)
            meta["real_source_coverage"] = round(
                len(real_sources) / total if total > 0 else 0, 3
            )
            meta["live_gate_status"] = "UNKNOWN"

            if self._include_sources:
                meta["mock_sources"] = [s.name for s in mock_sources]
                meta["real_sources"] = [s.name for s in real_sources]

        # Add disclaimer for DEMO mode
        if mode == "DEMO":
            meta["disclaimer"] = (
                "This response contains simulated data from mock sources. "
                "Not suitable for trading or investment decisions."
            )

        return meta
