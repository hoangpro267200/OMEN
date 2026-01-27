"""Signal endpoints (require API key via router dependencies)."""

from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query

from omen.api.dependencies import get_repository
from omen.application.ports.signal_repository import SignalRepository
from omen.infrastructure.security.auth import verify_api_key
from omen.infrastructure.security.redaction import redact_for_api

router = APIRouter()


@router.get("/")
async def list_signals(
    limit: int = Query(default=100, le=1000),
    offset: int = Query(default=0, ge=0),
    since: datetime | None = Query(default=None),
    repository: SignalRepository = Depends(get_repository),
    _api_key: str = Depends(verify_api_key),
) -> dict:
    """
    List recent signals with pagination.

    Returns redacted signals plus total, limit, and offset.
    """
    signals = repository.find_recent(limit=limit, offset=offset, since=since)
    total = repository.count(since=since)
    return {
        "signals": [redact_for_api(s) for s in signals],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/{signal_id}")
async def get_signal(
    signal_id: str,
    detail_level: Literal["minimal", "standard", "full"] = "standard",
    repository: SignalRepository = Depends(get_repository),
    _api_key: str = Depends(verify_api_key),
) -> dict:
    """Get a single signal by ID."""
    signal = repository.find_by_id(signal_id)
    if not signal:
        raise HTTPException(status_code=404, detail="Signal not found")
    return redact_for_api(signal, detail_level=detail_level)
