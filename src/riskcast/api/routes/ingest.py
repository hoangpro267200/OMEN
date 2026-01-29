"""
RiskCast Ingest API

POST /api/v1/signals/ingest — accept SignalEvent, persist, return ack_id.
Dedupe by signal_id: 409 with original ack_id on duplicate.
Persist-before-ack: store BEFORE returning 200.
"""

import logging
from datetime import datetime, timezone

import aiosqlite
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from omen.domain.models.signal_event import SignalEvent

from riskcast.infrastructure.signal_store import get_store

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["ingest"])


@router.post("/signals/ingest")
async def ingest_signal(request: Request) -> JSONResponse:
    """
    Ingest a signal (SignalEvent JSON).
    Idempotency: X-Idempotency-Key = signal_id.
    Returns 200 with ack_id on first accept; 409 with original ack_id on duplicate.
    """
    try:
        body = SignalEvent.model_validate(await request.json())
    except Exception as e:
        logger.warning("Invalid ingest body: %s", e)
        return JSONResponse(
            {"detail": str(e)},
            status_code=400,
        )
    store = get_store()
    source = request.headers.get("X-Replay-Source", "hot_path")
    now = datetime.now(timezone.utc)
    try:
        ack_id = await store.store(
            signal_id=body.signal_id,
            trace_id=body.deterministic_trace_id,
            source_event_id=body.source_event_id,
            ack_id=None,
            processed_at=now,
            emitted_at=body.emitted_at,
            source=source,
            signal_data=body.model_dump(mode="json"),
        )
        return JSONResponse({"ack_id": ack_id}, status_code=200)
    except aiosqlite.IntegrityError:
        rec = await store.get_by_signal_id(body.signal_id)
        ack_id = rec.ack_id if rec else "unknown"
        return JSONResponse(
            {"ack_id": ack_id, "duplicate": True},
            status_code=409,
        )
