"""Health check endpoints."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def health_check():
    """Basic health check."""
    return {"status": "healthy", "service": "omen"}


@router.get("/ready")
async def readiness_check():
    """Readiness check."""
    return {"status": "ready"}


@router.get("/live")
async def liveness_check():
    """Liveness check."""
    return {"status": "alive"}
