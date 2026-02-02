"""
Real-time price streaming via Server-Sent Events.
"""

import json
import logging
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from omen.infrastructure.realtime.price_streamer import get_price_streamer
from omen.infrastructure.security.auth import verify_api_key

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/realtime", tags=["Real-time"])


class SubscribeRequest(BaseModel):
    """Request to subscribe to signal updates."""

    signal_ids: list[str]


class SubscribeResponse(BaseModel):
    """Response from subscribe request."""

    subscribed: list[str]
    not_found: list[str]
    total_registered: int
    message: str


class RealtimeStatus(BaseModel):
    """Status of real-time streaming."""

    registered_signals: int
    websocket_connected: bool
    status: str
    registered_signal_ids: list[str]


async def get_streamer():
    """Return the global PriceStreamer and ensure it is started."""
    streamer = get_price_streamer()
    try:
        await streamer.start()
    except Exception:
        pass  # start() idempotent; ignore if already connected or connection in progress
    return streamer


@router.post("/subscribe", response_model=SubscribeResponse)
async def subscribe_signals(
    request: SubscribeRequest,
    api_key_id: Annotated[str, Depends(verify_api_key)],
) -> SubscribeResponse:
    """
    Subscribe to real-time price updates for signals.

    Only signals that have been processed by the pipeline and have
    valid token mappings can be subscribed to.
    """
    streamer = await get_streamer()
    if not request.signal_ids:
        return SubscribeResponse(
            subscribed=[],
            not_found=[],
            total_registered=streamer.get_registered_count(),
            message="No signal IDs provided",
        )
    subscribed = await streamer.subscribe_signals(request.signal_ids)
    not_found = [sid for sid in request.signal_ids if sid not in subscribed]
    if not_found:
        message = (
            f"Subscribed to {len(subscribed)} signals. "
            f"{len(not_found)} signals not registered for real-time."
        )
    else:
        message = f"Successfully subscribed to {len(subscribed)} signals"
    return SubscribeResponse(
        subscribed=subscribed,
        not_found=not_found,
        total_registered=streamer.get_registered_count(),
        message=message,
    )


@router.get("/prices")
async def stream_prices(
    api_key_id: Annotated[str, Depends(verify_api_key)],
) -> StreamingResponse:
    """
    Server-Sent Events stream of real-time price updates.

    Event types:
    - status: Connection status
    - data: Price update (default)
    - error: Error occurred
    - ping: Keepalive

    Returns immediately if not in streaming mode (for quick status check).
    """
    streamer = get_price_streamer()

    async def event_generator():
        # Initial status
        status_data = json.dumps(
            {
                "type": "connected",
                "registered_signals": streamer.get_registered_count(),
                "message": "Connected to OMEN real-time feed",
            }
        )
        yield f"event: status\ndata: {status_data}\n\n"

        if streamer.get_registered_count() == 0:
            warning_data = json.dumps(
                {
                    "type": "indicator",
                    "message": "No signals registered for real-time updates. Process signals first, then call /subscribe.",
                }
            )
            yield f"event: status\ndata: {warning_data}\n\n"

        # Try to start real-time streaming (non-fatal if it fails)
        try:
            await streamer.start()
        except Exception as e:
            err = json.dumps({"type": "error", "message": f"WebSocket unavailable: {e}"})
            yield f"event: error\ndata: {err}\n\n"

        # Stream updates (with keepalive)
        try:
            async for update in streamer.stream():
                data = json.dumps(
                    {
                        "signal_id": update.signal_id,
                        "probability": update.new_probability,
                        "previous_probability": update.old_probability,
                        "change_percent": update.change_percent,
                        "timestamp": update.timestamp,
                    }
                )
                yield f"data: {data}\n\n"
        except Exception as e:
            logger.exception("SSE stream error: %s", e)
            yield f"event: error\ndata: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "Access-Control-Allow-Origin": "*",
        },
    )


@router.get("/status", response_model=RealtimeStatus)
async def get_realtime_status(
    api_key_id: Annotated[str, Depends(verify_api_key)],
) -> RealtimeStatus:
    """Get current status of real-time streaming."""
    streamer = get_price_streamer()
    ws = getattr(streamer._ws_client, "_ws", None)
    return RealtimeStatus(
        registered_signals=streamer.get_registered_count(),
        websocket_connected=ws is not None,
        status="ready" if ws is not None else "idle",
        registered_signal_ids=streamer.get_registered_signals(),
    )


@router.post("/unsubscribe")
async def unsubscribe_signals(
    request: SubscribeRequest,
    api_key_id: Annotated[str, Depends(verify_api_key)],
) -> dict[str, list[str]]:
    """Unsubscribe from signals."""
    streamer = get_price_streamer()
    token_ids = [
        streamer.get_token_for_signal(sid)
        for sid in request.signal_ids
        if streamer.get_token_for_signal(sid)
    ]
    if token_ids and hasattr(streamer._ws_client, "unsubscribe"):
        await streamer._ws_client.unsubscribe(token_ids)
    return {"unsubscribed": request.signal_ids}
