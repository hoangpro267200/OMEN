"""
AISStream.io Real-time AIS Adapter
FREE tier: Unlimited WebSocket streaming
https://aisstream.io
"""

import os
import json
import asyncio
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum
import logging

logger = logging.getLogger(__name__)

try:
    import websockets
    from websockets.client import WebSocketClientProtocol
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False
    WebSocketClientProtocol = None


class VesselType(Enum):
    """AIS vessel type classification."""
    CARGO = "Cargo"
    TANKER = "Tanker"
    CONTAINER = "Container"
    BULK_CARRIER = "Bulk Carrier"
    PASSENGER = "Passenger"
    FISHING = "Fishing"
    TUG = "Tug"
    PILOT = "Pilot"
    SAR = "Search and Rescue"
    MILITARY = "Military"
    SAILING = "Sailing"
    PLEASURE = "Pleasure Craft"
    OTHER = "Other"


@dataclass
class VesselPosition:
    """Real-time vessel position from AIS."""
    mmsi: str
    name: Optional[str]
    vessel_type: VesselType
    latitude: float
    longitude: float
    speed_knots: float
    course: float
    heading: float
    destination: Optional[str]
    eta: Optional[str]
    ship_type_code: int
    timestamp: datetime
    
    @property
    def is_moving(self) -> bool:
        return self.speed_knots > 0.5
    
    @property
    def is_at_anchor(self) -> bool:
        return self.speed_knots < 0.3
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['vessel_type'] = self.vessel_type.value
        data['is_moving'] = self.is_moving
        data['is_at_anchor'] = self.is_at_anchor
        data['timestamp'] = self.timestamp.isoformat()
        return data


class AISStreamAdapter:
    """
    AISStream.io Real-time AIS Adapter.
    
    Features:
    - FREE unlimited real-time AIS data via WebSocket
    - Filter by geographic bounding boxes
    - Global coverage
    """
    
    WEBSOCKET_URL = "wss://stream.aisstream.io/v0/stream"
    
    TRADE_ROUTES = {
        "singapore_strait": [[1.0, 103.0], [1.5, 104.5]],
        "malacca_strait": [[1.0, 100.0], [6.0, 104.0]],
        "south_china_sea": [[5.0, 105.0], [25.0, 120.0]],
        "vietnam_coast": [[8.0, 104.0], [22.0, 110.0]],
        "shanghai_approach": [[30.0, 121.0], [32.0, 123.0]],
        "hong_kong": [[22.0, 113.5], [22.5, 114.5]],
        "suez_canal": [[29.5, 32.0], [31.5, 33.0]],
    }
    
    def __init__(self, api_key: Optional[str] = None):
        if not WEBSOCKETS_AVAILABLE:
            raise ImportError("websockets package required. Install with: pip install websockets")
        
        self.api_key = api_key or os.getenv("AISSTREAM_API_KEY", "")
        
        if not self.api_key:
            raise ValueError(
                "AISSTREAM_API_KEY not configured. "
                "Get free key at https://aisstream.io"
            )
        
        self._websocket: Optional[WebSocketClientProtocol] = None
        self._running = False
        self._callbacks: List[Callable[[VesselPosition], None]] = []
        self._vessels: Dict[str, VesselPosition] = {}
        
        logger.info("AISStreamAdapter initialized")
    
    def _parse_vessel_type(self, ship_type: int) -> VesselType:
        """Convert AIS ship type code to VesselType enum."""
        if 70 <= ship_type <= 79:
            if ship_type in [71, 72]:
                return VesselType.CONTAINER
            return VesselType.CARGO
        elif 80 <= ship_type <= 89:
            return VesselType.TANKER
        elif 60 <= ship_type <= 69:
            return VesselType.PASSENGER
        elif ship_type == 30:
            return VesselType.FISHING
        elif 31 <= ship_type <= 32:
            return VesselType.TUG
        elif ship_type == 50:
            return VesselType.PILOT
        elif ship_type == 51:
            return VesselType.SAR
        elif ship_type == 35:
            return VesselType.MILITARY
        elif ship_type == 36:
            return VesselType.SAILING
        elif ship_type == 37:
            return VesselType.PLEASURE
        return VesselType.OTHER
    
    def _parse_position_message(self, message: Dict[str, Any]) -> Optional[VesselPosition]:
        """Parse AIS position message to VesselPosition."""
        try:
            msg_type = message.get("MessageType", "")
            
            if msg_type not in ["PositionReport", "StandardClassBCSPositionReport", 
                               "ExtendedClassBPositionReport"]:
                return None
            
            meta = message.get("MetaData", {})
            msg_content = message.get("Message", {})
            
            pos = msg_content.get("PositionReport") or \
                  msg_content.get("StandardClassBCSPositionReport") or \
                  msg_content.get("ExtendedClassBPositionReport") or {}
            
            if not pos:
                return None
            
            time_utc = meta.get("time_utc", "")
            try:
                timestamp = datetime.fromisoformat(time_utc.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                timestamp = datetime.utcnow()
            
            ship_type_code = meta.get("ShipType", 0) or 0
            
            return VesselPosition(
                mmsi=str(meta.get("MMSI", "")),
                name=meta.get("ShipName") or None,
                vessel_type=self._parse_vessel_type(ship_type_code),
                latitude=pos.get("Latitude", 0) or 0,
                longitude=pos.get("Longitude", 0) or 0,
                speed_knots=pos.get("Sog", 0) or 0,
                course=pos.get("Cog", 0) or 0,
                heading=pos.get("TrueHeading", 0) or 0,
                destination=meta.get("Destination") or None,
                eta=None,
                ship_type_code=ship_type_code,
                timestamp=timestamp
            )
            
        except Exception as e:
            logger.debug(f"Failed to parse AIS message: {e}")
            return None
    
    def add_position_callback(self, callback: Callable[[VesselPosition], None]):
        """Add callback function for vessel position updates."""
        self._callbacks.append(callback)
    
    def remove_position_callback(self, callback: Callable[[VesselPosition], None]):
        """Remove callback function."""
        if callback in self._callbacks:
            self._callbacks.remove(callback)
    
    async def connect_and_stream(
        self,
        bounding_boxes: Optional[List[List[List[float]]]] = None,
        mmsi_filter: Optional[List[str]] = None,
        route_keys: Optional[List[str]] = None,
    ) -> None:
        """Connect to AIS stream and start receiving data."""
        boxes = []
        if route_keys:
            for key in route_keys:
                if key in self.TRADE_ROUTES:
                    boxes.append(self.TRADE_ROUTES[key])
        
        if bounding_boxes:
            boxes.extend(bounding_boxes)
        
        if not boxes:
            boxes = [
                self.TRADE_ROUTES["singapore_strait"],
                self.TRADE_ROUTES["vietnam_coast"],
            ]
        
        subscription = {
            "APIKey": self.api_key,
            "BoundingBoxes": boxes,
        }
        
        if mmsi_filter:
            subscription["FiltersShipMMSI"] = mmsi_filter
        
        self._running = True
        reconnect_delay = 5
        
        while self._running:
            try:
                logger.info(f"Connecting to AISStream WebSocket...")
                
                async with websockets.connect(
                    self.WEBSOCKET_URL,
                    ping_interval=30,
                    ping_timeout=10,
                ) as ws:
                    self._websocket = ws
                    logger.info("AISStream WebSocket connected")
                    
                    await ws.send(json.dumps(subscription))
                    logger.info(f"Subscribed to {len(boxes)} bounding boxes")
                    
                    reconnect_delay = 5
                    
                    async for message in ws:
                        if not self._running:
                            break
                        
                        try:
                            data = json.loads(message)
                            position = self._parse_position_message(data)
                            
                            if position and position.mmsi:
                                self._vessels[position.mmsi] = position
                                
                                for callback in self._callbacks:
                                    try:
                                        callback(position)
                                    except Exception as e:
                                        logger.warning(f"Callback error: {e}")
                                        
                        except json.JSONDecodeError:
                            continue
                            
            except Exception as e:
                logger.warning(f"AISStream connection error: {e}")
                if self._running:
                    await asyncio.sleep(reconnect_delay)
                    reconnect_delay = min(reconnect_delay * 2, 60)
        
        logger.info("AISStream stopped")
    
    async def stop(self):
        """Stop the AIS stream."""
        self._running = False
        if self._websocket:
            await self._websocket.close()
            self._websocket = None
    
    def get_cached_vessels(self) -> Dict[str, VesselPosition]:
        """Get all cached vessel positions."""
        return self._vessels.copy()
    
    def get_vessel_count_by_type(self) -> Dict[str, int]:
        """Get count of vessels by type."""
        counts: Dict[str, int] = {}
        for vessel in self._vessels.values():
            type_name = vessel.vessel_type.value
            counts[type_name] = counts.get(type_name, 0) + 1
        return counts
    
    async def get_snapshot(
        self,
        bounding_box: List[List[float]],
        duration_seconds: int = 30
    ) -> List[VesselPosition]:
        """Get a snapshot of vessels in an area over a short duration."""
        vessels: Dict[str, VesselPosition] = {}
        
        def collect(pos: VesselPosition):
            vessels[pos.mmsi] = pos
        
        self.add_position_callback(collect)
        
        stream_task = asyncio.create_task(
            self.connect_and_stream(bounding_boxes=[bounding_box])
        )
        
        try:
            await asyncio.sleep(duration_seconds)
        finally:
            await self.stop()
            stream_task.cancel()
            try:
                await stream_task
            except asyncio.CancelledError:
                pass
            
            self.remove_position_callback(collect)
        
        return list(vessels.values())


_adapter_instance: Optional[AISStreamAdapter] = None

def get_aisstream_adapter() -> AISStreamAdapter:
    """Get or create AISStream adapter instance."""
    global _adapter_instance
    if _adapter_instance is None:
        _adapter_instance = AISStreamAdapter()
    return _adapter_instance
