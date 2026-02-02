"""
WebSocket endpoint for real-time updates.

Uses DistributedConnectionManager for horizontal scaling via Redis Pub/Sub.

Broadcasts events:
- signal_emitted: New signal emitted
- signal_ingested: Signal ingested to RiskCast
- reconcile_started: Reconcile job started
- reconcile_completed: Reconcile job completed
- partition_sealed: Partition sealed
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from omen.infrastructure.realtime.distributed_connection_manager import (
    DistributedConnectionManager,
    get_connection_manager,
)

logger = logging.getLogger(__name__)

router = APIRouter()


# Legacy ConnectionManager for backward compatibility
# Now wraps DistributedConnectionManager
class ConnectionManager:
    """
    Manages WebSocket connections and broadcasting.
    
    Now uses DistributedConnectionManager for horizontal scaling.
    """

    def __init__(self) -> None:
        self._distributed: DistributedConnectionManager | None = None
        self._lock = asyncio.Lock()

    def _get_distributed(self) -> DistributedConnectionManager:
        """Get the distributed manager (lazy init)."""
        if self._distributed is None:
            self._distributed = get_connection_manager()
        return self._distributed

    @property
    def active_connections(self) -> set[WebSocket]:
        """Get active connections (for backward compatibility)."""
        dm = self._get_distributed()
        # Return local connections from the signals channel
        return dm.pubsub._local_connections.get(dm.CHANNEL_SIGNALS, set())

    async def connect(self, websocket: WebSocket) -> None:
        """Accept and register a new connection."""
        dm = self._get_distributed()
        await dm.connect(websocket, channel=dm.CHANNEL_SIGNALS)
        logger.info(
            "WebSocket connected. Local: %d, Redis: %s",
            dm.pubsub.get_local_connection_count(),
            "connected" if dm.pubsub.is_connected else "local-only",
        )

    async def disconnect(self, websocket: WebSocket) -> None:
        """Remove a connection."""
        dm = self._get_distributed()
        await dm.disconnect(websocket, channel=dm.CHANNEL_SIGNALS)
        logger.info(
            "WebSocket disconnected. Local: %d",
            dm.pubsub.get_local_connection_count(),
        )

    async def broadcast(self, event_type: str, data: dict[str, Any]) -> None:
        """Broadcast message to all connected clients (distributed)."""
        dm = self._get_distributed()
        await dm.broadcast_to_channel(
            channel=dm.CHANNEL_SIGNALS,
            event_type=event_type,
            data=data,
        )

    async def send_personal(
        self, websocket: WebSocket, event_type: str, data: dict[str, Any]
    ) -> None:
        """Send message to specific client."""
        message = {
            "type": event_type,
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
        }
        await websocket.send_text(json.dumps(message, default=str))


# Global connection manager (wraps distributed)
manager = ConnectionManager()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """
    WebSocket endpoint for real-time updates.

    Client can send:
    - {"type": "subscribe", "channels": ["signals", "reconcile"]}
    - {"type": "ping"}

    Server sends:
    - {"type": "signal_emitted", "data": {...}, "timestamp": "..."}
    - {"type": "pong"}
    """
    await manager.connect(websocket)

    try:
        while True:
            try:
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=30.0,
                )
                message = json.loads(data)

                if message.get("type") == "ping":
                    await manager.send_personal(websocket, "pong", {})

                elif message.get("type") == "subscribe":
                    channels = message.get("channels", [])
                    logger.info("Client subscribed to: %s", channels)

            except asyncio.TimeoutError:
                try:
                    await websocket.send_text(
                        json.dumps(
                            {
                                "type": "heartbeat",
                                "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
                            }
                        )
                    )
                except Exception:
                    break

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error("WebSocket error: %s", e)
    finally:
        await manager.disconnect(websocket)


# ═══════════════════════════════════════════════════════════════════════════════
# Broadcast Functions (call from other parts of the app)
# ═══════════════════════════════════════════════════════════════════════════════


async def broadcast_signal_emitted(
    signal_id: str, title: str, category: str, status: str
) -> None:
    """Broadcast when a signal is emitted."""
    await manager.broadcast(
        "signal_emitted",
        {
            "signal_id": signal_id,
            "title": title,
            "category": category,
            "status": status,
        },
    )


async def broadcast_signal_ingested(
    signal_id: str, ack_id: str, duplicate: bool
) -> None:
    """Broadcast when a signal is ingested to RiskCast."""
    await manager.broadcast(
        "signal_ingested",
        {
            "signal_id": signal_id,
            "ack_id": ack_id,
            "duplicate": duplicate,
            "status_code": 409 if duplicate else 200,
        },
    )


async def broadcast_reconcile_started(partition_date: str) -> None:
    """Broadcast when reconcile starts."""
    await manager.broadcast("reconcile_started", {"partition_date": partition_date})


async def broadcast_reconcile_completed(
    partition_date: str,
    status: str,
    replayed_count: int,
    replayed_ids: list[str],
) -> None:
    """Broadcast when reconcile completes."""
    await manager.broadcast(
        "reconcile_completed",
        {
            "partition_date": partition_date,
            "status": status,
            "replayed_count": replayed_count,
            "replayed_ids": replayed_ids,
        },
    )


async def broadcast_partition_sealed(partition_date: str) -> None:
    """Broadcast when a partition is sealed."""
    await manager.broadcast("partition_sealed", {"partition_date": partition_date})


async def broadcast_stats_update(stats: dict[str, Any]) -> None:
    """Broadcast stats update."""
    await manager.broadcast("stats_update", stats)
