"""
Polymarket WebSocket client for real-time price streaming.

WebSocket URL: wss://ws-subscriptions-clob.polymarket.com/ws/market
"""

import asyncio
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Callable

import websockets

from omen.domain.errors import SourceUnavailableError


@dataclass
class PriceUpdate:
    """Real-time price update from WebSocket."""

    market_id: str
    token_id: str
    price: float
    side: str  # "buy" or "sell"
    size: float
    timestamp: datetime


class PolymarketWebSocketClient:
    """
    WebSocket client for real-time Polymarket price updates.

    Usage:
        client = PolymarketWebSocketClient()
        await client.connect()
        await client.subscribe(["token_id_1", "token_id_2"])

        async for update in client.listen():
            print(f"Price update: {update}")
    """

    WS_URL = "wss://ws-subscriptions-clob.polymarket.com/ws/market"

    def __init__(self) -> None:
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
                self.WS_URL,
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

        Usage:
            async for update in client.listen():
                process(update)
        """
        if not self._ws:
            raise SourceUnavailableError("WebSocket not connected")

        while self._running:
            try:
                message = await asyncio.wait_for(
                    self._ws.recv(),
                    timeout=60.0,  # Reconnect if no message in 60s
                )

                data = json.loads(message)

                # Parse different message types
                if data.get("type") == "price_change":
                    update = PriceUpdate(
                        market_id=data.get("market", "") or "",
                        token_id=data.get("asset_id", "") or data.get("token_id", "") or "",
                        price=float(data.get("price", 0)),
                        side=data.get("side", "") or "",
                        size=float(data.get("size", 0)),
                        timestamp=datetime.utcnow(),
                    )

                    # Call registered callbacks
                    for callback in self._callbacks:
                        callback(update)

                    yield update

            except asyncio.TimeoutError:
                # Send ping to keep connection alive
                if self._ws:
                    await self._ws.ping()
            except websockets.ConnectionClosed:
                # Attempt reconnect
                await self._reconnect()
            except Exception as e:
                print(f"WebSocket error: {e}")  # noqa: T201
                await asyncio.sleep(1)

    async def _reconnect(self) -> None:
        """Attempt to reconnect and resubscribe."""
        tokens = list(self._subscribed_tokens)
        self._subscribed_tokens.clear()
        self._ws = None

        for attempt in range(3):
            try:
                await self.connect()
                if tokens:
                    await self.subscribe(tokens)
                return
            except Exception:
                await asyncio.sleep(2**attempt)

        raise SourceUnavailableError("WebSocket reconnection failed")
