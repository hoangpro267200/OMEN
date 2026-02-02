"""
Polymarket WebSocket client for real-time price streaming.

WebSocket URL from POLYMARKET_WS_URL (default: wss://ws-subscriptions-clob.polymarket.com/ws/market).
Reconnect with exponential backoff, max cap 30s.
"""

import asyncio
import json
import logging
import random
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable

import websockets

from omen.domain.errors import SourceUnavailableError
from omen.polymarket_settings import get_polymarket_settings

logger = logging.getLogger(__name__)

MAX_RECONNECT_BACKOFF_S = 30.0


@dataclass
class PriceUpdate:
    """Real-time price update from WebSocket."""

    market_id: str
    token_id: str
    price: float
    side: str  # "buy" or "sell"
    size: float
    timestamp: datetime


def _reconnect_backoff(attempt: int, base_s: float) -> float:
    """Exponential backoff with jitter, capped at MAX_RECONNECT_BACKOFF_S."""
    wait = base_s * (2**attempt) + random.uniform(0, 0.5)
    return min(wait, MAX_RECONNECT_BACKOFF_S)


class PolymarketWebSocketClient:
    """
    WebSocket client for real-time Polymarket price updates.

    URL from POLYMARKET_WS_URL. Reconnects with backoff on disconnect/timeout.
    """

    def __init__(self, ws_url: str | None = None):
        s = get_polymarket_settings()
        self._ws_url = (ws_url or s.ws_url).rstrip("/")
        self._backoff_base = s.retry_backoff_s
        self._ws: websockets.WebSocketClientProtocol | None = None
        self._subscribed_tokens: set[str] = set()
        self._callbacks: list[Callable[[PriceUpdate], None]] = []
        self._running = False

    async def connect(self) -> None:
        """Establish WebSocket connection. Idempotent if already connected."""
        if self._running and self._ws is not None:
            return
        try:
            self._ws = await websockets.connect(
                self._ws_url,
                ping_interval=30,
                ping_timeout=10,
            )
            self._running = True
        except Exception as e:
            raise SourceUnavailableError(f"WebSocket connection failed: {e}") from e

    async def disconnect(self) -> None:
        """Close WebSocket connection."""
        self._running = False
        if self._ws:
            await self._ws.close()
            self._ws = None

    async def subscribe(self, token_ids: list[str]) -> None:
        """
        Subscribe to price updates for specific tokens.

        Args:
            token_ids: List of condition token IDs to subscribe to
        """
        if not self._ws:
            raise SourceUnavailableError("WebSocket not connected")

        for token_id in token_ids:
            if token_id not in self._subscribed_tokens:
                message = {
                    "type": "subscribe",
                    "channel": "price",
                    "market": token_id,
                }
                await self._ws.send(json.dumps(message))
                self._subscribed_tokens.add(token_id)

    async def unsubscribe(self, token_ids: list[str]) -> None:
        """Unsubscribe from price updates."""
        if not self._ws:
            return

        for token_id in token_ids:
            if token_id in self._subscribed_tokens:
                message = {
                    "type": "unsubscribe",
                    "channel": "price",
                    "market": token_id,
                }
                await self._ws.send(json.dumps(message))
                self._subscribed_tokens.discard(token_id)

    def on_price_update(self, callback: Callable[[PriceUpdate], None]) -> None:
        """Register callback for price updates."""
        self._callbacks.append(callback)

    async def listen(self):
        """
        Listen for price updates (async generator).

        Reconnects with backoff on disconnect/timeout and resubscribes.
        """
        if not self._ws:
            raise SourceUnavailableError("WebSocket not connected")

        while self._running:
            try:
                message = await asyncio.wait_for(
                    self._ws.recv(),
                    timeout=60.0,
                )

                if not message or not message.strip():
                    continue

                try:
                    data = json.loads(message)
                except json.JSONDecodeError:
                    continue

                if data.get("type") == "price_change":
                    update = PriceUpdate(
                        market_id=data.get("market", "") or "",
                        token_id=data.get("asset_id", "") or data.get("token_id", "") or "",
                        price=float(data.get("price", 0)),
                        side=data.get("side", "") or "",
                        size=float(data.get("size", 0)),
                        timestamp=datetime.now(timezone.utc),
                    )
                    for callback in self._callbacks:
                        callback(update)
                    yield update

            except asyncio.TimeoutError:
                if self._ws:
                    await self._ws.ping()
            except websockets.ConnectionClosed:
                await self._reconnect()
            except Exception as e:
                if "Expecting value" not in str(e):
                    logger.warning("WebSocket error: %s", e)
                await asyncio.sleep(1)

    async def _reconnect(self) -> None:
        """Reconnect with exponential backoff and resubscribe. Max backoff 30s."""
        tokens = list(self._subscribed_tokens)
        self._subscribed_tokens.clear()
        self._ws = None

        for attempt in range(get_polymarket_settings().retry_max + 1):
            try:
                await self.connect()
                if tokens:
                    await self.subscribe(tokens)
                return
            except Exception as e:
                if attempt == get_polymarket_settings().retry_max:
                    raise SourceUnavailableError("WebSocket reconnection failed") from e
                wait = _reconnect_backoff(attempt, self._backoff_base)
                logger.warning(
                    "WebSocket reconnect attempt %s failed, retrying in %.1fs: %s",
                    attempt + 1,
                    wait,
                    e,
                )
                await asyncio.sleep(wait)

        raise SourceUnavailableError("WebSocket reconnection failed")
