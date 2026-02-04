"""
WebSocket endpoint for real-time updates.

Uses DistributedConnectionManager for horizontal scaling via Redis Pub/Sub.

Broadcasts events:
- signal_emitted: New signal emitted
- signal_ingested: Signal ingested to RiskCast
- reconcile_started: Reconcile job started
- reconcile_completed: Reconcile job completed
- partition_sealed: Partition sealed

Authentication:
- WebSocket connections require API key via query parameter: ?api_key=YOUR_KEY
- RBAC scope required: read:realtime
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status

from omen.api.route_dependencies import Scopes
from omen.infrastructure.realtime.distributed_connection_manager import (
    DistributedConnectionManager,
    get_connection_manager,
)
from omen.infrastructure.security.unified_auth import AuthContext, authenticate

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


async def _authenticate_websocket(websocket: WebSocket) -> AuthContext | None:
    """
    Authenticate WebSocket connection using API key from query parameters.

    Returns AuthContext if authenticated, None if authentication failed.
    WebSocket authentication requires ?api_key= query parameter since
    browsers cannot set custom headers on WebSocket connections.
    """
    # Extract API key from query parameters
    api_key = websocket.query_params.get("api_key")

    if not api_key:
        logger.warning("WebSocket connection rejected: No API key provided")
        return None

    try:
        # Authenticate using unified auth
        # For WebSocket, we pass the key directly (no header support in WS)
        auth = await authenticate(
            request=websocket,  # WebSocket is request-like for our purposes
            api_key_header=None,
            api_key_query=api_key,
        )

        # Check for realtime scope
        if Scopes.REALTIME_READ not in auth.scopes and "*" not in auth.scopes and Scopes.ADMIN not in auth.scopes:
            logger.warning(
                "WebSocket connection rejected: User %s lacks %s scope",
                auth.user_id,
                Scopes.REALTIME_READ,
            )
            return None

        logger.info("WebSocket authenticated: user=%s", auth.user_id)
        return auth

    except Exception as e:
        logger.warning("WebSocket authentication failed: %s", e)
        return None


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """
    WebSocket endpoint for real-time updates.

    Authentication:
    - Requires API key via query parameter: ws://host/ws?api_key=YOUR_KEY
    - Required scope: read:realtime

    Client can send:
    - {"type": "subscribe", "channels": ["signals", "reconcile"]}
    - {"type": "ping"}

    Server sends:
    - {"type": "signal_emitted", "data": {...}, "timestamp": "..."}
    - {"type": "pong"}
    - {"type": "error", "message": "..."} on auth failure
    """
    # Authenticate before accepting connection
    auth = await _authenticate_websocket(websocket)

    if auth is None:
        # Reject connection with 4001 (custom code for auth failure)
        # Standard codes: 4000-4999 are reserved for application use
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await manager.connect(websocket)

    try:
        # Send welcome message with auth info
        await manager.send_personal(
            websocket,
            "connected",
            {"user_id": auth.user_id, "scopes": auth.scopes},
        )

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
                    logger.info("Client %s subscribed to: %s", auth.user_id, channels)

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
        logger.error("WebSocket error for user %s: %s", auth.user_id, e)
    finally:
        await manager.disconnect(websocket)


# ═══════════════════════════════════════════════════════════════════════════════
# Broadcast Functions (call from other parts of the app)
# ═══════════════════════════════════════════════════════════════════════════════


async def broadcast_signal_emitted(signal_id: str, title: str, category: str, status: str) -> None:
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


async def broadcast_signal_ingested(signal_id: str, ack_id: str, duplicate: bool) -> None:
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
