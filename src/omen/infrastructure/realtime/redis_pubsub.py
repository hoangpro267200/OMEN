"""
Redis Pub/Sub for distributed WebSocket state.

Enables horizontal scaling of real-time features by using Redis
as a message broker between multiple OMEN instances.

Architecture:
    Instance 1 ──┐                    ┌── WebSocket Client A
    Instance 2 ──┼── Redis Pub/Sub ──┼── WebSocket Client B
    Instance 3 ──┘                    └── WebSocket Client C

Each instance:
1. Publishes signals to Redis
2. Subscribes to Redis channels
3. Forwards messages to local WebSocket connections
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import socket
import uuid
from datetime import datetime
from typing import Any, Callable, Dict, Optional, Set

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class RedisMessage(BaseModel):
    """Message format for Redis Pub/Sub."""

    channel: str
    event_type: str
    payload: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    sender_instance: str


class RedisPubSubManager:
    """
    Distributed Pub/Sub manager using Redis.

    Replaces in-memory ConnectionManager for horizontal scaling.
    Falls back to local-only mode if Redis is unavailable.
    """

    def __init__(
        self,
        redis_url: Optional[str] = None,
        instance_id: Optional[str] = None,
        channel_prefix: str = "omen:realtime:",
    ):
        self.redis_url = redis_url or os.getenv("REDIS_URL")
        self.instance_id = instance_id or self._generate_instance_id()
        self.channel_prefix = channel_prefix

        self._redis = None
        self._pubsub = None
        self._listener_task: Optional[asyncio.Task] = None
        self._connected = False

        # Local WebSocket connections (per instance)
        self._local_connections: Dict[str, Set[Any]] = {}

        # Message handlers
        self._handlers: Dict[str, Callable] = {}

    def _generate_instance_id(self) -> str:
        """Generate unique instance ID."""
        hostname = socket.gethostname()
        return f"{hostname}-{uuid.uuid4().hex[:8]}"

    @property
    def is_connected(self) -> bool:
        """Check if Redis is connected."""
        return self._connected

    async def connect(self) -> bool:
        """
        Initialize Redis connection and start listener.

        Returns True if connected, False if falling back to local mode.
        """
        if not self.redis_url:
            logger.warning(
                "REDIS_URL not configured, running in local-only mode. "
                "WebSocket state will NOT be shared across instances."
            )
            return False

        try:
            import redis.asyncio as redis

            self._redis = redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
            )

            # Test connection
            await self._redis.ping()

            self._pubsub = self._redis.pubsub()
            self._connected = True

            # Start background listener
            self._listener_task = asyncio.create_task(self._listen())

            logger.info(
                "Redis Pub/Sub connected (instance: %s)",
                self.instance_id,
            )
            return True

        except ImportError:
            logger.warning("redis package not installed. Install with: pip install redis[hiredis]")
            return False
        except Exception as e:
            logger.warning(
                "Failed to connect to Redis: %s. Running in local-only mode.",
                e,
            )
            self._connected = False
            return False

    async def disconnect(self) -> None:
        """Cleanup connections."""
        if self._listener_task:
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass

        if self._pubsub:
            await self._pubsub.close()

        if self._redis:
            await self._redis.close()

        self._connected = False
        logger.info("Redis Pub/Sub disconnected")

    async def subscribe(self, channel: str, handler: Callable) -> None:
        """
        Subscribe to a channel.

        Args:
            channel: Channel name (without prefix)
            handler: Async function to handle messages
        """
        full_channel = f"{self.channel_prefix}{channel}"
        self._handlers[full_channel] = handler

        if self._pubsub:
            await self._pubsub.subscribe(full_channel)
            logger.debug("Subscribed to channel: %s", full_channel)

    async def unsubscribe(self, channel: str) -> None:
        """Unsubscribe from a channel."""
        full_channel = f"{self.channel_prefix}{channel}"
        self._handlers.pop(full_channel, None)

        if self._pubsub:
            await self._pubsub.unsubscribe(full_channel)

    async def publish(
        self,
        channel: str,
        event_type: str,
        payload: Dict[str, Any],
    ) -> int:
        """
        Publish message to channel.

        Returns:
            Number of subscribers that received the message (0 if local-only mode)
        """
        full_channel = f"{self.channel_prefix}{channel}"

        message = RedisMessage(
            channel=channel,
            event_type=event_type,
            payload=payload,
            sender_instance=self.instance_id,
        )

        if self._redis and self._connected:
            try:
                count = await self._redis.publish(
                    full_channel,
                    message.model_dump_json(),
                )
                return count
            except Exception as e:
                logger.error("Failed to publish to Redis: %s", e)
                return 0

        return 0

    async def _listen(self) -> None:
        """Background task to listen for messages from Redis."""
        while True:
            try:
                message = await self._pubsub.get_message(
                    ignore_subscribe_messages=True,
                    timeout=1.0,
                )

                if message and message["type"] == "message":
                    channel = message["channel"]
                    data = json.loads(message["data"])

                    # Skip messages from self (already handled locally)
                    if data.get("sender_instance") == self.instance_id:
                        continue

                    # Call registered handler
                    handler = self._handlers.get(channel)
                    if handler:
                        try:
                            await handler(RedisMessage(**data))
                        except Exception as e:
                            logger.error(
                                "Error in message handler for %s: %s",
                                channel,
                                e,
                            )

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Error in Redis listener: %s", e)
                await asyncio.sleep(1)

    # ═══════════════════════════════════════════════════════════════════════
    # LOCAL WEBSOCKET MANAGEMENT
    # ═══════════════════════════════════════════════════════════════════════

    def add_local_connection(self, channel: str, websocket: Any) -> None:
        """Add WebSocket connection to local tracking."""
        if channel not in self._local_connections:
            self._local_connections[channel] = set()
        self._local_connections[channel].add(websocket)
        logger.debug(
            "Added local connection to %s (total: %d)",
            channel,
            len(self._local_connections[channel]),
        )

    def remove_local_connection(self, channel: str, websocket: Any) -> None:
        """Remove WebSocket connection from local tracking."""
        if channel in self._local_connections:
            self._local_connections[channel].discard(websocket)
            logger.debug(
                "Removed local connection from %s (total: %d)",
                channel,
                len(self._local_connections[channel]),
            )

    async def broadcast_to_local(
        self,
        channel: str,
        message: Dict[str, Any],
    ) -> int:
        """Broadcast to local WebSocket connections."""
        connections = self._local_connections.get(channel, set())
        sent = 0
        disconnected = []

        for websocket in connections:
            try:
                await websocket.send_json(message)
                sent += 1
            except Exception:
                # Connection closed, mark for removal
                disconnected.append(websocket)

        # Clean up disconnected
        for ws in disconnected:
            self._local_connections[channel].discard(ws)

        return sent

    def get_local_connection_count(self, channel: Optional[str] = None) -> int:
        """Get count of local connections."""
        if channel:
            return len(self._local_connections.get(channel, set()))
        return sum(len(conns) for conns in self._local_connections.values())

    async def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the pub/sub system."""
        return {
            "instance_id": self.instance_id,
            "redis_connected": self._connected,
            "local_channels": len(self._local_connections),
            "local_connections": self.get_local_connection_count(),
            "subscribed_channels": len(self._handlers),
        }


# Global instance
_pubsub_manager: Optional[RedisPubSubManager] = None


def get_pubsub_manager() -> RedisPubSubManager:
    """Get or create the global Redis Pub/Sub manager."""
    global _pubsub_manager
    if _pubsub_manager is None:
        _pubsub_manager = RedisPubSubManager()
    return _pubsub_manager


async def initialize_pubsub() -> bool:
    """Initialize the global Pub/Sub manager."""
    manager = get_pubsub_manager()
    return await manager.connect()


async def shutdown_pubsub() -> None:
    """Shutdown the global Pub/Sub manager."""
    global _pubsub_manager
    if _pubsub_manager:
        await _pubsub_manager.disconnect()
        _pubsub_manager = None
