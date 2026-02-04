"""
FastAPI entrypoint with security middleware.

All endpoints require authentication except explicitly whitelisted public endpoints.
"""

# ═══════════════════════════════════════════════════════════════════════════════
# CRITICAL: Load environment variables FIRST, before any other imports
# This ensures all modules see the correct env vars from .env file
# ═══════════════════════════════════════════════════════════════════════════════
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root (3 levels up from main.py: src/omen/main.py -> project root)
_env_path = Path(__file__).resolve().parent.parent.parent / ".env"
if _env_path.exists():
    load_dotenv(_env_path)
    print(f"[OMEN] Loaded environment from: {_env_path}")
else:
    print(f"[OMEN] Warning: No .env file found at {_env_path}")

# ═══════════════════════════════════════════════════════════════════════════════

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
    calibration,  # P1-4: Historical validation endpoints
    explanations,
    health,
    live,
    live_mode,
    methodology,
    metrics_circuit,
    metrics_prometheus,
    multi_source,
    # partner_risk removed - deprecated, all endpoints return 410
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
from omen.infrastructure.observability.tracing import (
    setup_tracing,
    setup_all_instrumentations,
    is_tracing_enabled,
)
from omen.infrastructure.middleware.live_gate_middleware import LiveGateMiddleware
from omen.infrastructure.middleware.response_wrapper import ResponseWrapperMiddleware
from omen.infrastructure.observability.logging import setup_logging
from omen.infrastructure.security.config import get_security_config
from omen.infrastructure.security.middleware import (
    HTTPSRedirectMiddleware,
    AuditLoggingMiddleware,
)
from omen.infrastructure.security.rate_limit import rate_limit_middleware
# NOTE: Authentication is handled by unified_auth module via route dependencies
# ScopeChecker/require_scopes are DEPRECATED - use unified auth instead
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
from omen.jobs import JobScheduler
from omen.domain.services import get_trust_manager

logger = logging.getLogger(__name__)

# Environment
OMEN_ENV = os.getenv("OMEN_ENV", "development")
IS_PRODUCTION = OMEN_ENV == "production"

# Global state for cleanup on shutdown (register via register_writer / register_emitter)
_active_writers: list[Any] = []
_active_emitters: list[Any] = []
_job_scheduler: Any = None  # JobScheduler instance


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
async def lifespan(app: FastAPI):  # type: ignore[arg-type]
    """
    Application lifespan: startup and graceful shutdown.

    Startup: log, register signal handlers (Unix), initialize distributed components.
    Shutdown: drain in-flight requests, flush writers, close emitters, cleanup distributed.
    """
    from omen.infrastructure.realtime.distributed_connection_manager import (
        initialize_connection_manager,
        shutdown_connection_manager,
    )

    # === RUN PRODUCTION STARTUP CHECKS ===
    # Must run FIRST before any other initialization
    if IS_PRODUCTION:
        from omen.infrastructure.startup_checks import run_production_checks
        run_production_checks()  # Exits if checks fail
    
    omen_config = get_config()
    setup_logging(
        level=omen_config.log_level,
        json_format=omen_config.log_format == "json",
        service_name="omen",
    )
    config = get_security_config()

    # Additional API key check (duplicates startup check but provides better error message)
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

    # === SETUP DISTRIBUTED TRACING (OpenTelemetry) ===
    try:
        tracer = setup_tracing(
            service_name="omen",
            sample_rate=0.1 if IS_PRODUCTION else 1.0,  # Sample 10% in prod
        )
        if is_tracing_enabled():
            logger.info("OpenTelemetry distributed tracing enabled")
        else:
            logger.info("OpenTelemetry tracing not configured (OTLP_ENDPOINT not set)")
    except Exception as e:
        logger.warning("Failed to setup distributed tracing: %s", e)

    # === REGISTER HEALTH CHECKS FOR ALL DATA SOURCES ===
    from omen.infrastructure.health.source_health_registration import (
        register_all_health_sources,
    )
    
    register_all_health_sources()
    # Note: Initial health check skipped for faster startup - will run on first /health/sources request
    logger.info("Health checks registered (initial check will run on first request)")

    # === PRODUCTION GATE: Validate data sources ===
    from omen.infrastructure.data_integrity import get_source_registry, validate_live_mode
    
    registry = get_source_registry()
    registry.initialize()
    
    can_go_live, blockers = validate_live_mode()
    
    if IS_PRODUCTION:
        # In production, log warnings about mock sources
        if not can_go_live:
            logger.warning(
                "PRODUCTION DATA WARNING: %d mock sources detected. LIVE mode will be blocked.",
                len(blockers)
            )
            for blocker in blockers:
                logger.warning("  - %s", blocker)
    else:
        # In development, just log status
        if can_go_live:
            logger.info("LIVE mode ALLOWED - all data sources are real")
        else:
            logger.info("LIVE mode BLOCKED - %d mock sources: %s", len(blockers), blockers[:3])

    # Seed demo signals in development mode
    if not IS_PRODUCTION:
        try:
            from omen.application.container import get_container
            from data.demo_signals import DEMO_SIGNALS
            from omen.domain.models.omen_signal import OmenSignal, ConfidenceLevel, SignalCategory
            from datetime import datetime, timezone
            
            container = get_container()
            repo = container.repository
            
            # Category mapping
            cat_map = {
                "GEOPOLITICAL": SignalCategory.GEOPOLITICAL,
                "INFRASTRUCTURE": SignalCategory.INFRASTRUCTURE,
                "CLIMATE": SignalCategory.WEATHER,
                "COMPLIANCE": SignalCategory.REGULATORY,
                "OPERATIONAL": SignalCategory.OTHER,
                "FINANCIAL": SignalCategory.ECONOMIC,
            }
            
            seeded = 0
            now = datetime.now(timezone.utc)
            from datetime import timedelta
            import random
            
            for i, raw in enumerate(DEMO_SIGNALS):
                cat_str = raw.get("category", "OTHER")
                category = cat_map.get(cat_str, SignalCategory.OTHER)
                conf_str = raw.get("confidence_level", "MEDIUM")
                confidence_level = (
                    ConfidenceLevel.HIGH if conf_str == "HIGH"
                    else ConfidenceLevel.LOW if conf_str == "LOW"
                    else ConfidenceLevel.MEDIUM
                )
                
                # Vary timestamps to look realistic (within last few hours)
                time_offset = timedelta(minutes=random.randint(5, 180))
                signal_time = now - time_offset
                
                # Ensure demo signals have DEMO prefix
                signal_id = raw["id"]
                if not signal_id.startswith("OMEN-DEMO"):
                    signal_id = f"OMEN-DEMO{signal_id.replace('OMEN-', '')}"
                
                signal = OmenSignal(
                    signal_id=signal_id,
                    source_event_id=f"demo-{raw['id']}",
                    title=raw["title"],
                    description=raw.get("description", ""),
                    probability=float(raw["probability"]),
                    confidence_score=float(raw["confidence_score"]),
                    confidence_level=confidence_level,
                    category=category,
                    ruleset_version="1.0.0",
                    trace_id=f"trace-{raw['id'][:12]}",
                    observed_at=signal_time,
                    generated_at=signal_time + timedelta(seconds=random.randint(1, 30)),
                )
                repo.save(signal)
                seeded += 1
            
            # Update rejection tracker with demo stats
            from omen.infrastructure.debug.rejection_tracker import get_rejection_tracker
            tracker = get_rejection_tracker()
            for raw in DEMO_SIGNALS:
                tracker.record_passed(
                    signal_id=raw["id"],
                    event_id=f"demo-{raw['id']}",
                    title=raw["title"],
                    probability=float(raw["probability"]),
                    confidence=float(raw["confidence_score"]),
                    confidence_level=raw.get("confidence_level", "MEDIUM"),
                )
            
            # Update metrics collector for UI stats
            from omen.infrastructure.metrics.pipeline_metrics import get_metrics_collector
            metrics = get_metrics_collector()
            metrics.complete_batch(
                events_received=len(DEMO_SIGNALS),
                events_validated=len(DEMO_SIGNALS),
                events_translated=len(DEMO_SIGNALS),
                signals_generated=len(DEMO_SIGNALS),
                events_rejected=0,
                avg_confidence=sum(float(s["confidence_score"]) for s in DEMO_SIGNALS) / len(DEMO_SIGNALS),
            )
            
            logger.info("Seeded %d demo signals for development", seeded)
        except Exception as e:
            logger.warning("Could not seed demo signals: %s", e)
    
    # === RUN POSTGRESQL MIGRATIONS (if DATABASE_URL is set) ===
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        try:
            from omen.infrastructure.database.postgres_migrations import PostgresMigrationRunner
            import asyncpg  # type: ignore[import-not-found]
            
            pool = await asyncpg.create_pool(database_url, min_size=1, max_size=2)
            try:
                runner = PostgresMigrationRunner(pool)
                applied = await runner.run()
                if applied:
                    logger.info("Applied %d PostgreSQL migrations: %s", len(applied), applied)
                else:
                    logger.info("PostgreSQL schema is up to date")
            finally:
                await pool.close()
        except ImportError:
            logger.debug("asyncpg not installed, skipping PostgreSQL migrations")
        except Exception as e:
            logger.warning("PostgreSQL migrations failed (non-fatal): %s", e)
    
    # === INITIALIZE SOURCE TRUST MANAGER ===
    try:
        trust_manager = get_trust_manager()
        logger.info("Source trust manager initialized with %d sources", len(trust_manager.DEFAULT_TRUST_SCORES))
    except Exception as e:
        logger.warning("Failed to initialize trust manager: %s", e)

    # === EAGERLY INITIALIZE MULTI-SOURCE AGGREGATOR ===
    # This ensures all adapters are initialized at startup, not on first request
    try:
        from omen.adapters.inbound.multi_source import get_multi_source_aggregator
        aggregator = get_multi_source_aggregator()
        source_list = aggregator.list_sources()
        logger.info(
            "Multi-source aggregator initialized with %d sources: %s",
            len(source_list),
            [s["name"] for s in source_list],
        )
    except Exception as e:
        logger.warning("Failed to initialize multi-source aggregator: %s", e)
    
    # === START JOB SCHEDULER ===
    global _job_scheduler
    if database_url:
        # Use PostgreSQL-backed scheduler when DATABASE_URL is available
        try:
            import asyncpg  # type: ignore[import-not-found]
            
            pool = await asyncpg.create_pool(database_url, min_size=2, max_size=5)
            _job_scheduler = JobScheduler(pool)
            await _job_scheduler.start()
            logger.info("Job scheduler started with %d cleanup jobs (PostgreSQL mode)", len(_job_scheduler.list_jobs()))
        except ImportError:
            logger.debug("asyncpg not installed, job scheduler disabled")
        except Exception as e:
            logger.warning("Failed to start job scheduler: %s", e)
    else:
        # P1-5: Use InMemoryJobScheduler when DATABASE_URL is not set
        try:
            from omen.jobs.in_memory_scheduler import start_in_memory_scheduler
            _job_scheduler = await start_in_memory_scheduler()
            logger.info("InMemoryJobScheduler started with %d cleanup jobs (no DATABASE_URL)", len(_job_scheduler.list_jobs()))
        except Exception as e:
            logger.warning("Failed to start in-memory job scheduler: %s", e)
    
    # === BACKGROUND SIGNAL GENERATOR ===
    # Start immediately rather than lazy start for better data freshness
    try:
        from omen.infrastructure.background.signal_generator import start_background_generator
        start_background_generator()
        logger.info("Background signal generator started")
    except Exception as e:
        logger.warning("Failed to start background signal generator: %s", e)

    # Initialize Redis state manager (for caching, distributed locks, etc.)
    from omen.infrastructure.redis import initialize_redis, shutdown_redis
    try:
        redis_connected = await initialize_redis()
        if redis_connected:
            logger.info("Redis state manager initialized (distributed mode)")
        else:
            logger.info("Redis state manager initialized (in-memory fallback)")
    except Exception as e:
        logger.warning("Failed to initialize Redis state manager: %s", e)

    # Initialize distributed WebSocket manager
    try:
        await initialize_connection_manager()
        logger.info("Distributed connection manager initialized")
    except Exception as e:
        logger.warning("Failed to initialize distributed connection manager: %s", e)

    # Register signal handlers (Unix only - Windows doesn't support add_signal_handler)
    try:
        loop = asyncio.get_running_loop()
        # SIGTERM and SIGINT are Unix signals - not available on Windows
        sigterm = getattr(signal, "SIGTERM", None)
        sigint = getattr(signal, "SIGINT", None)
        for sig in (sigterm, sigint):
            if sig is not None:
                loop.add_signal_handler(
                    sig,
                    lambda s=sig: _on_signal(s),  # type: ignore[misc]
                )
    except NotImplementedError:
        # Windows: add_signal_handler not available
        pass
    except Exception as e:
        logger.debug("Could not add signal handlers: %s", e)

    yield

    logger.info("OMEN shutting down gracefully...")
    
    # Stop background signal generator if it was started
    try:
        from omen.infrastructure.background.signal_generator import get_background_generator
        generator = get_background_generator()
        if generator.is_running:
            generator.stop()
            logger.info("Background signal generator stopped")
    except Exception as e:
        logger.warning("Error stopping background signal generator: %s", e)
    
    # Stop job scheduler if running
    if _job_scheduler is not None:
        try:
            await _job_scheduler.stop()
            logger.info("Job scheduler stopped")
        except Exception as e:
            logger.warning("Error stopping job scheduler: %s", e)
        _job_scheduler = None
    
    await graceful_shutdown(timeout_seconds=30)

    # Shutdown distributed components
    try:
        await shutdown_connection_manager()
        logger.info("Distributed connection manager shutdown")
    except Exception as e:
        logger.error("Error shutting down connection manager: %s", e)

    # Shutdown Redis state manager
    try:
        from omen.infrastructure.redis import shutdown_redis
        await shutdown_redis()
        logger.info("Redis state manager shutdown")
    except Exception as e:
        logger.error("Error shutting down Redis: %s", e)

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

    # === OPENTELEMETRY INSTRUMENTATION ===
    if is_tracing_enabled():
        try:
            setup_all_instrumentations(app)
            logger.info("OpenTelemetry instrumentation enabled for FastAPI, HTTPX, AsyncPG, Redis")
        except Exception as e:
            logger.warning("Failed to setup OpenTelemetry instrumentation: %s", e)

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

    # Trace context injection (trace_id, request_id for observability)
    app.middleware("http")(trace_context_middleware)
    logger.info("Trace context middleware enabled (request tracing)")

    # Rate limiting
    if config.rate_limit_enabled:
        app.middleware("http")(rate_limit_middleware)

    # Live Gate Middleware - Enforces LIVE/DEMO mode at request level
    app.add_middleware(
        LiveGateMiddleware,
        strict_mode=False,  # Downgrade to DEMO instead of 403
        excluded_paths=["/health", "/ready", "/metrics", "/docs", "/openapi.json", "/redoc"],
    )
    logger.info("LiveGateMiddleware enabled (graceful mode - downgrades to DEMO)")

    # Response Wrapper Middleware - Adds metadata envelope to JSON responses
    app.add_middleware(
        ResponseWrapperMiddleware,
        excluded_paths=["/health", "/ready", "/metrics", "/docs", "/openapi.json", "/redoc", "/ws"],
        include_sources=True,
    )
    logger.info("ResponseWrapperMiddleware enabled (JSON responses wrapped with metadata)")

    # ✅ Security Headers Middleware (ACTIVATED)
    # Uses proper middleware class instead of inline function
    from omen.infrastructure.middleware.security_headers import SecurityHeadersMiddleware
    app.add_middleware(SecurityHeadersMiddleware, enable_hsts=IS_PRODUCTION)
    logger.info("✅ SecurityHeadersMiddleware ACTIVATED (OWASP compliant)")
    
    # OMEN-specific headers and CORS handling
    @app.middleware("http")
    async def add_omen_headers(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        response = await call_next(request)
        # OMEN contract headers
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

    # Calibration API (P1-4: Historical validation)
    app.include_router(
        calibration.router,
        prefix="/api/v1",
        tags=["Calibration"],
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

    # Partner Risk Engine - REMOVED (was deprecated, all endpoints returned 410)
    # Use partner_signals.router instead for Vietnamese logistics monitoring

    # UI API (for demo frontend) - uses read:signals scope
    # NOTE: Mounted at /api/v1/ui to match frontend OMEN_API_BASE expectation
    app.include_router(
        ui.router,
        prefix="/api/v1/ui",
        tags=["UI"],
        dependencies=READ_SIGNALS,  # 🔒 RBAC: read:signals
    )
    
    # Also mount at /api/ui for backwards compatibility
    app.include_router(
        ui.router,
        prefix="/api/ui",
        tags=["UI (Legacy)"],
        dependencies=READ_SIGNALS,  # 🔒 RBAC: read:signals
        include_in_schema=False,  # Hide from OpenAPI docs
    )

    # LIVE Mode Status API - Backend-authoritative LIVE/DEMO validation
    app.include_router(
        live_mode.router,
        prefix="/api/v1",
        tags=["Live Mode"],
        dependencies=READ_SIGNALS,  # 🔒 RBAC: read:signals
    )

    # LIVE Data API - Real-time data from all sources
    from omen.api.routes import live_data
    app.include_router(
        live_data.router,
        prefix="/api/v1/live-data",
        tags=["Live Data"],
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
