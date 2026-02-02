"""
Distributed WebSocket Connection Manager.

Uses Redis Pub/Sub for cross-instance communication, enabling
horizontal scaling of WebSocket connections.

Features:
- Cross-instance message broadcasting via Redis
- Local connection tracking per instance
- Automatic fallback to local-only mode if Redis unavailable
- Channel-based subscriptions
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Set

from fastapi import WebSocket

from omen.infrastructure.realtime.redis_pubsub import (
    RedisPubSubManager,
    RedisMessage,
    get_pubsub_manager,
)

logger = logging.getLogger(__name__)


class DistributedConnectionManager:
    """
    Distributed WebSocket Connection Manager.

    Replaces in-memory ConnectionManager for horizontal scaling.
    Uses Redis Pub/Sub for cross-instance message broadcasting.
    """

    # Standard channels
    CHANNEL_SIGNALS = "signals"
    CHANNEL_PRICES = "prices"
    CHANNEL_ALERTS = "alerts"
    CHANNEL_STATS = "stats"

    def __init__(self, pubsub: Optional[RedisPubSubManager] = None):
        self.pubsub = pubsub or get_pubsub_manager()
        self._initialized = False
        self._lock = asyncio.Lock()

    async def initialize(self) -> None:
        """Initialize and subscribe to channels."""
        if self._initialized:
            return

        # Connect to Redis
        await self.pubsub.connect()

        # Subscribe to broadcast channels
        await self.pubsub.subscribe(
            self.CHANNEL_SIGNALS,
            self._handle_signal_broadcast,
        )
        await self.pubsub.subscribe(
            self.CHANNEL_PRICES,
            self._handle_price_broadcast,
        )
        await self.pubsub.subscribe(
            self.CHANNEL_ALERTS,
            self._handle_alert_broadcast,
        )
        await self.pubsub.subscribe(
            self.CHANNEL_STATS,
            self._handle_stats_broadcast,
        )

        self._initialized = True
        logger.info(
            "Distributed Connection Manager initialized (redis: %s)",
            "connected" if self.pubsub.is_connected else "local-only",
        )

    async def shutdown(self) -> None:
        """Cleanup."""
        await self.pubsub.disconnect()
        self._initialized = False

    # ═══════════════════════════════════════════════════════════════════════
    # CONNECTION MANAGEMENT
    # ═══════════════════════════════════════════════════════════════════════

    async def connect(
        self,
        websocket: WebSocket,
        channel: str = CHANNEL_SIGNALS,
    ) -> None:
        """Accept WebSocket connection and track it."""
        await websocket.accept()
        self.pubsub.add_local_connection(channel, websocket)

        # Send welcome message
        await websocket.send_json(
            {
                "type": "connected",
                "channel": channel,
                "instance": self.pubsub.instance_id,
                "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
                "redis_connected": self.pubsub.is_connected,
            }
        )

        logger.info(
            "WebSocket connected to channel %s (local connections: %d)",
            channel,
            self.pubsub.get_local_connection_count(channel),
        )

    async def disconnect(
        self,
        websocket: WebSocket,
        channel: str = CHANNEL_SIGNALS,
    ) -> None:
        """Remove WebSocket connection."""
        self.pubsub.remove_local_connection(channel, websocket)
        logger.info(
            "WebSocket disconnected from channel %s (local connections: %d)",
            channel,
            self.pubsub.get_local_connection_count(channel),
        )

    # ═══════════════════════════════════════════════════════════════════════
    # BROADCASTING
    # ═══════════════════════════════════════════════════════════════════════

    async def broadcast_signal(self, signal_data: Dict[str, Any]) -> int:
        """
        Broadcast signal to all connected clients across all instances.

        Returns total local clients reached.
        """
        message = {"type": "signal", "data": signal_data}

        # Publish to Redis (reaches other instances)
        await self.pubsub.publish(
            self.CHANNEL_SIGNALS,
            "signal",
            signal_data,
        )

        # Also broadcast to local connections immediately
        return await self.pubsub.broadcast_to_local(
            self.CHANNEL_SIGNALS,
            message,
        )

    async def broadcast_price(self, price_data: Dict[str, Any]) -> int:
        """Broadcast price update."""
        message = {"type": "price", "data": price_data}

        await self.pubsub.publish(
            self.CHANNEL_PRICES,
            "price",
            price_data,
        )

        return await self.pubsub.broadcast_to_local(
            self.CHANNEL_PRICES,
            message,
        )

    async def broadcast_alert(self, alert_data: Dict[str, Any]) -> int:
        """Broadcast alert."""
        message = {"type": "alert", "data": alert_data}

        await self.pubsub.publish(
            self.CHANNEL_ALERTS,
            "alert",
            alert_data,
        )

        return await self.pubsub.broadcast_to_local(
            self.CHANNEL_ALERTS,
            message,
        )

    async def broadcast_stats(self, stats_data: Dict[str, Any]) -> int:
        """Broadcast stats update."""
        message = {"type": "stats_update", "data": stats_data}

        await self.pubsub.publish(
            self.CHANNEL_STATS,
            "stats_update",
            stats_data,
        )

        return await self.pubsub.broadcast_to_local(
            self.CHANNEL_STATS,
            message,
        )

    async def broadcast_to_channel(
        self,
        channel: str,
        event_type: str,
        data: Dict[str, Any],
    ) -> int:
        """Generic broadcast to any channel."""
        message = {"type": event_type, "data": data}

        await self.pubsub.publish(channel, event_type, data)

        return await self.pubsub.broadcast_to_local(channel, message)

    # ═══════════════════════════════════════════════════════════════════════
    # MESSAGE HANDLERS (from Redis)
    # ═══════════════════════════════════════════════════════════════════════

    async def _handle_signal_broadcast(self, message: RedisMessage) -> None:
        """Handle signal broadcast from other instances."""
        await self.pubsub.broadcast_to_local(
            self.CHANNEL_SIGNALS,
            {"type": "signal", "data": message.payload},
        )

    async def _handle_price_broadcast(self, message: RedisMessage) -> None:
        """Handle price broadcast from other instances."""
        await self.pubsub.broadcast_to_local(
            self.CHANNEL_PRICES,
            {"type": "price", "data": message.payload},
        )

    async def _handle_alert_broadcast(self, message: RedisMessage) -> None:
        """Handle alert broadcast from other instances."""
        await self.pubsub.broadcast_to_local(
            self.CHANNEL_ALERTS,
            {"type": "alert", "data": message.payload},
        )

    async def _handle_stats_broadcast(self, message: RedisMessage) -> None:
        """Handle stats broadcast from other instances."""
        await self.pubsub.broadcast_to_local(
            self.CHANNEL_STATS,
            {"type": "stats_update", "data": message.payload},
        )

    # ═══════════════════════════════════════════════════════════════════════
    # STATISTICS
    # ═══════════════════════════════════════════════════════════════════════

    async def get_stats(self) -> Dict[str, Any]:
        """Get connection manager statistics."""
        pubsub_stats = await self.pubsub.get_stats()
        return {
            **pubsub_stats,
            "initialized": self._initialized,
            "channels": {
                self.CHANNEL_SIGNALS: self.pubsub.get_local_connection_count(self.CHANNEL_SIGNALS),
                self.CHANNEL_PRICES: self.pubsub.get_local_connection_count(self.CHANNEL_PRICES),
                self.CHANNEL_ALERTS: self.pubsub.get_local_connection_count(self.CHANNEL_ALERTS),
                self.CHANNEL_STATS: self.pubsub.get_local_connection_count(self.CHANNEL_STATS),
            },
        }


# Global instance
_connection_manager: Optional[DistributedConnectionManager] = None


def get_connection_manager() -> DistributedConnectionManager:
    """Get or create the global distributed connection manager."""
    global _connection_manager
    if _connection_manager is None:
        _connection_manager = DistributedConnectionManager()
    return _connection_manager


async def initialize_connection_manager() -> None:
    """Initialize the global connection manager."""
    manager = get_connection_manager()
    await manager.initialize()


async def shutdown_connection_manager() -> None:
    """Shutdown the global connection manager."""
    global _connection_manager
    if _connection_manager:
        await _connection_manager.shutdown()
        _connection_manager = None
