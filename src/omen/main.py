"""FastAPI entrypoint with security middleware."""

import warnings
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from omen.api.routes import explanations, health, live, realtime, signals
from omen.infrastructure.security.auth import verify_api_key
from omen.infrastructure.security.config import get_security_config
from omen.infrastructure.security.rate_limit import rate_limit_middleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    config = get_security_config()
    if not config.api_keys:
        warnings.warn(
            "No API keys configured! Set OMEN_SECURITY_API_KEYS environment variable.",
            UserWarning,
            stacklevel=1,
        )
    yield


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    config = get_security_config()

    app = FastAPI(
        title="OMEN Intelligence API",
        description="Signal intelligence engine for logistics risk",
        version="2.0.0",
        lifespan=lifespan,
    )

    if config.cors_enabled:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=config.cors_origins,
            allow_credentials=config.cors_allow_credentials,
            allow_methods=["GET", "POST"],
            allow_headers=["*"],
        )

    if config.rate_limit_enabled:
        app.middleware("http")(rate_limit_middleware)

    @app.middleware("http")
    async def add_security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )
        return response

    app.include_router(health.router, prefix="/health", tags=["Health"])
    app.include_router(
        signals.router,
        prefix="/api/v1/signals",
        tags=["Signals"],
        dependencies=[Depends(verify_api_key)],
    )
    app.include_router(
        explanations.router,
        prefix="/api/v1",
        tags=["Explanations"],
        dependencies=[Depends(verify_api_key)],
    )
    app.include_router(live.router, prefix="/api/v1")
    app.include_router(stats.router, prefix="/api/v1")
    app.include_router(activity.router, prefix="/api/v1")
    app.include_router(realtime.router, prefix="/api/v1")

    @app.get("/")
    async def root():
        """Root endpoint."""
        return {"message": "OMEN Signal Processing Pipeline"}

    return app


app = create_app()
