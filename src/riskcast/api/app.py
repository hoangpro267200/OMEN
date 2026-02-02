"""RiskCast FastAPI app (ingest + reconcile)."""

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI

from riskcast.api.routes import ingest_router, reconcile_router
from riskcast.api.routes.metrics import metrics

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Run database migrations on startup."""
    try:
        from omen.infrastructure.database.migrations import run_riskcast_migrations

        db_path = os.environ.get("RISKCAST_DB_PATH", "/var/lib/riskcast/signals.db")
        await run_riskcast_migrations(db_path)
    except Exception as e:
        logger.warning("Migrations on startup failed (non-fatal): %s", e)
    yield


app = FastAPI(title="RiskCast", version="0.1.0", lifespan=lifespan)
app.include_router(ingest_router)
app.include_router(reconcile_router)


@app.get("/health")
async def health():
    """Health check for load balancers and Docker."""
    return {"status": "ok"}


@app.get("/metrics")
async def metrics_endpoint():
    """Prometheus metrics endpoint."""
    return await metrics()
