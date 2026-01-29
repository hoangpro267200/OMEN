"""RiskCast FastAPI app (ingest + reconcile)."""

from fastapi import FastAPI

from riskcast.api.routes import ingest_router, reconcile_router

app = FastAPI(title="RiskCast", version="0.1.0")
app.include_router(ingest_router)
app.include_router(reconcile_router)
