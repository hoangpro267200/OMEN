"""
Real-time price streaming service for UI.
"""

from collections.abc import Callable
from dataclasses import dataclass

from omen.adapters.inbound.polymarket.websocket_client import (
    PolymarketWebSocketClient,
    PriceUpdate,
)


@dataclass
class SignalPriceUpdate:
    """Price update mapped to OMEN signal."""

    signal_id: str
    new_probability: float
    old_probability: float
    change_percent: float
    timestamp: str


class PriceStreamer:
    """
    Service that streams real-time price updates.

    Used by:
    - API Server (push to UI via Server-Sent Events)
    - Background processor (trigger reprocessing on significant changes)
    """

    def __init__(self) -> None:
        self._ws_client = PolymarketWebSocketClient()
        self._signal_token_map: dict[str, str] = {}  # signal_id -> token_id
        self._token_signal_map: dict[str, str] = {}  # token_id -> signal_id
        self._last_prices: dict[str, float] = {}  # token_id -> last price
        self._callbacks: list[Callable[[SignalPriceUpdate], None]] = []

    async def start(self) -> None:
        """Start the price streaming service."""
        await self._ws_client.connect()

    async def stop(self) -> None:
        """Stop the price streaming service."""
        await self._ws_client.disconnect()

    def register_signal(self, signal_id: str, token_id: str, initial_price: float) -> None:
        """Register a signal for price updates."""
        self._signal_token_map[signal_id] = token_id
        self._token_signal_map[token_id] = signal_id
        self._last_prices[token_id] = initial_price

    def on_update(self, callback: Callable[[SignalPriceUpdate], None]) -> None:
        """Register callback for signal price updates."""
        self._callbacks.append(callback)

    async def subscribe_signals(self, signal_ids: list[str]) -> None:
        """Subscribe to updates for registered signals."""
        token_ids = [
            self._signal_token_map[sid]
            for sid in signal_ids
            if sid in self._signal_token_map
        ]
        if token_ids:
            await self._ws_client.subscribe(token_ids)

    async def stream(self):
        """
        Stream price updates as SignalPriceUpdate.

        Usage:
            async for update in streamer.stream():
                broadcast_to_ui(update)
        """
        async for price_update in self._ws_client.listen():
            token_id = price_update.token_id

            if token_id not in self._token_signal_map:
                continue

            signal_id = self._token_signal_map[token_id]
            old_price = self._last_prices.get(token_id, 0.5)
            new_price = price_update.price

            # Update stored price
            self._last_prices[token_id] = new_price

            # Calculate change
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
                callback(update)

            yield update
