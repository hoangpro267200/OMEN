"""
Real-time endpoints for UI streaming.
"""

import json

from fastapi import APIRouter, Body
from fastapi.responses import StreamingResponse

from omen.infrastructure.realtime.price_streamer import PriceStreamer


router = APIRouter(prefix="/realtime", tags=["Real-time"])

# Global streamer instance (in production, use proper DI)
_streamer: PriceStreamer | None = None


async def get_streamer() -> PriceStreamer:
    """Return or create the global PriceStreamer and ensure it is started."""
    global _streamer
    if _streamer is None:
        _streamer = PriceStreamer()
        await _streamer.start()
    return _streamer


@router.get("/prices")
async def stream_prices():
    """
    Server-Sent Events endpoint for real-time price updates.

    Usage in React:
        const eventSource = new EventSource('/api/v1/realtime/prices');
        eventSource.onmessage = (event) => {
            const update = JSON.parse(event.data);
            updateSignalPrice(update.signal_id, update.new_probability);
        };
    """
    streamer = await get_streamer()

    async def event_generator():
        async for update in streamer.stream():
            data = json.dumps({
                "signal_id": update.signal_id,
                "probability": update.new_probability,
                "change_percent": update.change_percent,
                "timestamp": update.timestamp,
            })
            yield f"data: {data}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


@router.post("/subscribe")
async def subscribe_signals(signal_ids: list[str] = Body(..., embed=False)):
    """Subscribe to price updates for specific signals."""
    streamer = await get_streamer()
    await streamer.subscribe_signals(signal_ids)
    return {"status": "subscribed", "signals": signal_ids}
