"""
FastAPI entrypoint with security middleware.

All endpoints require authentication except explicitly whitelisted public endpoints.
"""

import asyncio
import logging
import os
import signal
import warnings
from collections.abc import Awaitable, Callable
from contextlib import asynccontextmanager
from typing import Any

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import Response

from omen.api.routes import (
    activity,
    explanations,
    health,
    live,
    methodology,
    metrics_circuit,
    metrics_prometheus,
    multi_source,
    partner_risk,
    partner_signals,
    realtime,
    signals,
    stats,
    storage,
    ui,
    websocket,
)
from omen.api.errors import register_error_handlers
from omen.config import get_config
from omen.infrastructure.middleware.request_tracking import (
    get_active_request_count,
    is_shutting_down,
    request_tracking_middleware,
    set_shutdown,
    wait_for_requests_to_drain,
)
from omen.infrastructure.middleware.trace_context import trace_context_middleware
from omen.infrastructure.middleware.http_metrics import http_metrics_middleware
from omen.infrastructure.observability.logging import setup_logging
from omen.infrastructure.security.auth import verify_api_key
from omen.infrastructure.security.config import get_security_config
from omen.infrastructure.security.middleware import (
    AuthenticationMiddleware,
    HTTPSRedirectMiddleware,
    AuditLoggingMiddleware,
)
from omen.infrastructure.security.rate_limit import rate_limit_middleware
from omen.infrastructure.security.rbac import Scopes, require_scopes
from omen.api.security import (
    READ_SIGNALS,
    WRITE_SIGNALS,
    READ_PARTNERS,
    READ_MULTI_SOURCE,
    READ_REALTIME,
    READ_ACTIVITY,
    READ_STATS,
    READ_METHODOLOGY,
    READ_STORAGE,
    DEBUG_ONLY,
)

logger = logging.getLogger(__name__)

# Environment
OMEN_ENV = os.getenv("OMEN_ENV", "development")
IS_PRODUCTION = OMEN_ENV == "production"

# Global state for cleanup on shutdown (register via register_writer / register_emitter)
_active_writers: list[Any] = []
_active_emitters: list[Any] = []


def register_writer(writer: Any) -> None:
    """Register a ledger writer for flush on shutdown."""
    _active_writers.append(writer)


def register_emitter(emitter: Any) -> None:
    """Register an emitter for close on shutdown."""
    _active_emitters.append(emitter)


async def _drain_in_flight_operations() -> None:
    """Wait for all in-flight HTTP requests to complete."""
    while get_active_request_count() > 0:
        await asyncio.sleep(0.1)


async def graceful_shutdown(timeout_seconds: int = 30) -> None:
    """
    Graceful shutdown sequence:
    1. Mark shutdown (health returns 503)
    2. Wait for in-flight requests (max timeout)
    3. Flush all registered ledger writers
    4. Close all registered emitter HTTP clients
    """
    set_shutdown()
    try:
        await asyncio.wait_for(
            _drain_in_flight_operations(),
            timeout=timeout_seconds,
        )
    except asyncio.TimeoutError:
        logger.error(
            "Graceful shutdown timed out after %ss, forcing...",
            timeout_seconds,
        )

    for writer in _active_writers:
        try:
            await writer.flush_and_close()
            logger.info("Flushed ledger writer: %s", type(writer).__name__)
        except Exception as e:
            logger.error("Error flushing ledger writer: %s", e)

    for emitter in _active_emitters:
        try:
            await emitter.close()
            logger.info("Closed emitter: %s", type(emitter).__name__)
        except Exception as e:
            logger.error("Error closing emitter: %s", e)


def _on_signal(sig: int) -> None:
    """Sync callback for signal handlers: mark shutdown (health returns 503)."""
    logger.warning(
        "Received signal %s, initiating graceful shutdown...",
        sig,
    )
    set_shutdown()


@asynccontextmanager
async def lifespan(app: FastAPI) -> Any:
    """
    Application lifespan: startup and graceful shutdown.

    Startup: log, register signal handlers (Unix), initialize distributed components.
    Shutdown: drain in-flight requests, flush writers, close emitters, cleanup distributed.
    """
    from omen.infrastructure.realtime.distributed_connection_manager import (
        initialize_connection_manager,
        shutdown_connection_manager,
    )

    omen_config = get_config()
    setup_logging(
        level=omen_config.log_level,
        json_format=omen_config.log_format == "json",
        service_name="omen",
    )
    config = get_security_config()

    # CRITICAL: Fail fast in production if no API keys configured
    if not config.get_api_keys():
        if IS_PRODUCTION:
            raise RuntimeError(
                "CRITICAL: No API keys configured in production! "
                "Set OMEN_SECURITY_API_KEYS environment variable. "
                "Cannot start OMEN without authentication in production."
            )
        else:
            warnings.warn(
                "No API keys configured! Set OMEN_SECURITY_API_KEYS environment variable. "
                "This would be a fatal error in production.",
                UserWarning,
                stacklevel=1,
            )

    logger.info("OMEN starting up (env=%s)...", OMEN_ENV)

    # Initialize distributed WebSocket manager
    try:
        await initialize_connection_manager()
        logger.info("Distributed connection manager initialized")
    except Exception as e:
        logger.warning("Failed to initialize distributed connection manager: %s", e)

    try:
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(
                sig,
                lambda s=sig: _on_signal(s),  # type: ignore[misc]
            )
    except NotImplementedError:
        # Windows: add_signal_handler not available for SIGTERM
        pass
    except Exception as e:
        logger.debug("Could not add signal handlers: %s", e)

    yield

    logger.info("OMEN shutting down gracefully...")
    await graceful_shutdown(timeout_seconds=30)

    # Shutdown distributed components
    try:
        await shutdown_connection_manager()
        logger.info("Distributed connection manager shutdown")
    except Exception as e:
        logger.error("Error shutting down connection manager: %s", e)

    logger.info("OMEN shutdown complete.")


# Maximum request body size (10MB default)
MAX_REQUEST_BODY_SIZE = int(os.getenv("OMEN_MAX_REQUEST_BODY_SIZE", str(10 * 1024 * 1024)))


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    config = get_security_config()

    app = FastAPI(
        title="OMEN Signal Intelligence API",
        description="""
## Signal Intelligence Engine

OMEN transforms market events into structured probability signals.

### Authentication

All API endpoints require authentication via API key.
Include the `X-API-Key` header in all requests.

**Public endpoints (no auth required):**
- `/health/*` - Health checks
- `/docs`, `/redoc` - API documentation
- `/metrics` - Prometheus metrics

### What OMEN provides
- Probability assessment with confidence bounds
- Signal validation and quality scoring
- Geographic and temporal context
- Full evidence chain and traceability

### What OMEN does NOT provide
- Impact assessment (severity, delay, cost)
- Decision steering (temporal proximity, relevance rank, high-confidence flags)
- Recommendations or advice
- Risk quantification

Impact assessment is the responsibility of downstream systems.
        """.strip(),
        version="2.0.0",
        lifespan=lifespan,
    )

    # === ERROR HANDLERS (register early) ===
    register_error_handlers(app)

    # === REQUEST BODY SIZE LIMIT ===
    @app.middleware("http")
    async def limit_request_body(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        """
        Limit request body size to prevent DoS attacks.

        Returns 413 Payload Too Large if body exceeds MAX_REQUEST_BODY_SIZE.
        """
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                size = int(content_length)
                if size > MAX_REQUEST_BODY_SIZE:
                    from fastapi.responses import JSONResponse

                    return JSONResponse(
                        status_code=413,
                        content={
                            "error": "PAYLOAD_TOO_LARGE",
                            "message": f"Request body too large. Max size: {MAX_REQUEST_BODY_SIZE} bytes",
                            "max_size_bytes": MAX_REQUEST_BODY_SIZE,
                        },
                    )
            except ValueError:
                pass
        return await call_next(request)

    # === MIDDLEWARE STACK (order matters - last added runs first) ===

    # HTTPS Redirect (production only, runs first)
    if IS_PRODUCTION:
        app.add_middleware(HTTPSRedirectMiddleware)
        logger.info("HTTPS redirect middleware enabled (production)")

    # CORS middleware
    if config.cors_enabled:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=config.get_cors_origins(),
            allow_credentials=config.cors_allow_credentials,
            allow_methods=["GET", "POST", "OPTIONS"],
            allow_headers=["*"],
        )

    # Audit logging for authenticated requests
    app.add_middleware(AuditLoggingMiddleware)

    # Request tracking
    app.middleware("http")(request_tracking_middleware)

    # HTTP metrics (p50, p95, p99 latency tracking)
    app.middleware("http")(http_metrics_middleware)

    # Rate limiting
    if config.rate_limit_enabled:
        app.middleware("http")(rate_limit_middleware)

    # Security headers
    @app.middleware("http")
    async def add_security_headers(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["X-OMEN-Contract-Version"] = "2.0.0"
        response.headers["X-OMEN-Contract-Type"] = "signal-only"
        # Ensure CORS headers are present for cross-origin requests
        origin = request.headers.get("origin")
        if origin:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "*"
        return response

    # === PUBLIC ROUTES (no authentication required) ===

    # Health checks - always public
    app.include_router(health.router, prefix="/health", tags=["Health"])

    # Metrics - public for Prometheus scraping
    app.include_router(metrics_prometheus.router, tags=["Metrics"])

    # Root endpoint
    @app.get("/", tags=["Root"])
    async def root() -> dict[str, str]:
        """Root endpoint - public."""
        return {
            "message": "OMEN Signal Intelligence API",
            "version": "2.0.0",
            "docs": "/docs",
            "health": "/health",
        }

    # === PROTECTED ROUTES (authentication + RBAC required) ===

    # Signals API - core functionality
    # GET: read:signals, POST: write:signals
    app.include_router(
        signals.router,
        prefix="/api/v1/signals",
        tags=["Signals"],
        dependencies=READ_SIGNALS,  # 🔒 RBAC: read:signals
    )

    # Explanations API
    app.include_router(
        explanations.router,
        prefix="/api/v1",
        tags=["Explanations"],
        dependencies=READ_SIGNALS,  # 🔒 RBAC: read:signals
    )

    # Live data API (requires write access)
    app.include_router(
        live.router,
        prefix="/api/v1",
        tags=["Live Data"],
        dependencies=WRITE_SIGNALS,  # 🔒 RBAC: write:signals
    )

    # Circuit breaker metrics
    app.include_router(
        metrics_circuit.router,
        prefix="/api/v1",
        tags=["Circuit Breaker"],
        dependencies=READ_STATS,  # 🔒 RBAC: read:stats
    )

    # Storage API
    app.include_router(
        storage.router,
        prefix="/api/v1",
        tags=["Storage"],
        dependencies=READ_STORAGE,  # 🔒 RBAC: read:storage
    )

    # Stats API
    app.include_router(
        stats.router,
        prefix="/api/v1",
        tags=["Statistics"],
        dependencies=READ_STATS,  # 🔒 RBAC: read:stats
    )

    # Activity API
    app.include_router(
        activity.router,
        prefix="/api/v1",
        tags=["Activity"],
        dependencies=READ_ACTIVITY,  # 🔒 RBAC: read:activity
    )

    # Realtime API
    app.include_router(
        realtime.router,
        prefix="/api/v1",
        tags=["Realtime"],
        dependencies=READ_REALTIME,  # 🔒 RBAC: read:realtime
    )

    # Methodology API
    app.include_router(
        methodology.router,
        prefix="/api/v1",
        tags=["Methodology"],
        dependencies=READ_METHODOLOGY,  # 🔒 RBAC: read:methodology
    )

    # Multi-source Intelligence API
    app.include_router(
        multi_source.router,
        prefix="/api/v1/multi-source",
        tags=["Multi-Source Intelligence"],
        dependencies=READ_MULTI_SOURCE,  # 🔒 RBAC: read:multi-source
    )

    # WebSocket (has its own auth)
    app.include_router(websocket.router, tags=["WebSocket"])

    # Partner Signals Engine - Pure Signal API
    app.include_router(
        partner_signals.router,
        prefix="/api/v1",
        tags=["Partner Signals"],
        dependencies=READ_PARTNERS,  # 🔒 RBAC: read:partners
    )

    # Partner Risk Engine - DEPRECATED
    app.include_router(
        partner_risk.router,
        prefix="/api/v1/partner-risk",
        tags=["Partner Risk (DEPRECATED)"],
        dependencies=READ_PARTNERS,  # 🔒 RBAC: read:partners
    )

    # UI API (for demo frontend) - uses read:signals scope
    app.include_router(
        ui.router,
        prefix="/api/ui",
        tags=["UI"],
        dependencies=READ_SIGNALS,  # 🔒 RBAC: read:signals
    )

    # === DEBUG ROUTES (development only, requires debug scope) ===

    if not IS_PRODUCTION:
        from omen.api.routes import debug

        app.include_router(
            debug.router,
            prefix="/api/v1",
            tags=["Debug (DEV ONLY)"],
            dependencies=DEBUG_ONLY,  # 🔒 RBAC: debug scope required
        )
        logger.info("Debug routes enabled (non-production environment)")
    else:
        logger.info("Debug routes DISABLED (production environment)")

    return app


app = create_app()
