"""
Real-time price streaming service for UI.

Pipeline registers signals via register_signal(signal_id, token_id, initial_price).
API subscribes via subscribe_signals(signal_ids) and streams updates from stream().

Uses broadcast pattern: one WebSocket listener broadcasts to multiple SSE clients.
"""

import asyncio
import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Optional

from omen.adapters.inbound.polymarket.websocket_client import (
    PolymarketWebSocketClient,
    PriceUpdate,
)

logger = logging.getLogger(__name__)


@dataclass
class SignalPriceUpdate:
    """Price update mapped to OMEN signal."""

    signal_id: str
    new_probability: float
    old_probability: float
    change_percent: float
    timestamp: str


def get_price_streamer() -> "PriceStreamer":
    """Return the global PriceStreamer singleton (used by pipeline and API)."""
    global _price_streamer
    if _price_streamer is None:
        _price_streamer = PriceStreamer()
    return _price_streamer


_price_streamer: Optional["PriceStreamer"] = None


class PriceStreamer:
    """
    Service that streams real-time price updates.

    Uses broadcast pattern: one background task reads from WebSocket and
    broadcasts to all subscribed SSE clients via asyncio.Queue.
    """

    def __init__(self) -> None:
        self._ws_client = PolymarketWebSocketClient()
        self._signal_token_map: dict[str, str] = {}  # signal_id -> token_id
        self._token_signal_map: dict[str, str] = {}  # token_id -> signal_id
        self._last_prices: dict[str, float] = {}  # token_id -> last price
        self._callbacks: list[Callable[[SignalPriceUpdate], None]] = []
        # Broadcast to multiple SSE clients
        self._subscribers: list[asyncio.Queue[SignalPriceUpdate]] = []
        self._broadcaster_task: Optional[asyncio.Task] = None
        self._started = False

    async def start(self) -> None:
        """Start the price streaming service and broadcaster."""
        if self._started:
            return
        try:
            await self._ws_client.connect()
            self._started = True
            # Start the broadcaster task
            if self._broadcaster_task is None or self._broadcaster_task.done():
                self._broadcaster_task = asyncio.create_task(self._broadcast_loop())
        except Exception as e:
            logger.warning("WebSocket connect failed: %s", e)
            raise

    async def stop(self) -> None:
        """Stop the price streaming service."""
        self._started = False
        if self._broadcaster_task and not self._broadcaster_task.done():
            self._broadcaster_task.cancel()
            try:
                await self._broadcaster_task
            except asyncio.CancelledError:
                pass
        await self._ws_client.disconnect()

    async def _broadcast_loop(self) -> None:
        """Background task that reads WebSocket and broadcasts to all subscribers."""
        try:
            async for price_update in self._ws_client.listen():
                token_id = price_update.token_id
                if token_id not in self._token_signal_map:
                    continue

                signal_id = self._token_signal_map[token_id]
                old_price = self._last_prices.get(token_id, 0.5)
                new_price = price_update.price

                self._last_prices[token_id] = new_price

                if old_price > 0:
                    change_percent = ((new_price - old_price) / old_price) * 100
                else:
                    change_percent = 0.0

                update = SignalPriceUpdate(
                    signal_id=signal_id,
                    new_probability=new_price,
                    old_probability=old_price,
                    change_percent=change_percent,
                    timestamp=price_update.timestamp.isoformat(),
                )

                # Call callbacks
                for callback in self._callbacks:
                    try:
                        callback(update)
                    except Exception:
                        pass

                # Broadcast to all SSE subscribers
                for queue in list(self._subscribers):
                    try:
                        queue.put_nowait(update)
                    except asyncio.QueueFull:
                        pass  # Drop if subscriber is slow
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.exception("Broadcaster loop error: %s", e)

    def register_signal(self, signal_id: str, token_id: str, initial_price: float) -> None:
        """Register a signal for price updates. Called by the pipeline when a signal is generated."""
        self._signal_token_map[signal_id] = token_id
        self._token_signal_map[token_id] = signal_id
        self._last_prices[token_id] = initial_price

    def get_registered_count(self) -> int:
        """Number of signals registered for real-time updates."""
        return len(self._signal_token_map)

    def get_registered_signals(self) -> list[str]:
        """List of signal IDs that are registered for real-time updates."""
        return list(self._signal_token_map.keys())

    def get_token_for_signal(self, signal_id: str) -> Optional[str]:
        """Return the token ID for a registered signal, or None."""
        return self._signal_token_map.get(signal_id)

    def is_registered(self, signal_id: str) -> bool:
        """Whether a signal is registered for real-time updates."""
        return signal_id in self._signal_token_map

    def on_update(self, callback: Callable[[SignalPriceUpdate], None]) -> None:
        """Register callback for signal price updates."""
        self._callbacks.append(callback)

    async def subscribe_signals(self, signal_ids: list[str]) -> list[str]:
        """Subscribe to updates for registered signals. Returns list of signal_ids that were subscribed."""
        token_ids: list[str] = []
        subscribed: list[str] = []
        for sid in signal_ids:
            if sid in self._signal_token_map:
                token_ids.append(self._signal_token_map[sid])
                subscribed.append(sid)
        if token_ids:
            try:
                await self._ws_client.subscribe(token_ids)
            except Exception as e:
                logger.warning("Subscribe failed: %s", e)
        return subscribed

    async def stream(self):
        """
        Stream price updates as SignalPriceUpdate.

        Each caller gets its own Queue to receive broadcasts.
        Usage:
            async for update in streamer.stream():
                broadcast_to_ui(update)
        """
        queue: asyncio.Queue[SignalPriceUpdate] = asyncio.Queue(maxsize=100)
        self._subscribers.append(queue)
        try:
            while True:
                try:
                    update = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield update
                except asyncio.TimeoutError:
                    # No update in 30s, continue waiting (SSE keepalive)
                    continue
        finally:
            # Remove from subscribers when SSE client disconnects
            if queue in self._subscribers:
                self._subscribers.remove(queue)
