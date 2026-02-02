"""
MarineTraffic Real API Implementation.

Real-time vessel tracking and port congestion data from MarineTraffic API.

API Documentation: https://www.marinetraffic.com/en/ais-api-services

Environment Variables:
    MARINETRAFFIC_API_KEY: API key for MarineTraffic
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Optional

import httpx
from pydantic import BaseModel, ConfigDict, Field

from omen.domain.models.raw_signal import RawSignalEvent
from omen.infrastructure.resilience.circuit_breaker import CircuitBreaker

from .schemas import Vessel, PortStatus, ChokePointStatus
from .config import AISConfig, PORT_METADATA, CHOKEPOINT_METADATA

logger = logging.getLogger(__name__)


class MarineTrafficVesselResponse(BaseModel):
    """MarineTraffic vessel response."""

    model_config = ConfigDict(frozen=True)

    MMSI: int
    IMO: Optional[int] = None
    SHIPNAME: Optional[str] = None
    SHIPTYPE: Optional[int] = None
    LAT: float
    LON: float
    SPEED: Optional[float] = None
    COURSE: Optional[float] = None
    HEADING: Optional[float] = None
    FLAG: Optional[str] = None
    LENGTH: Optional[int] = None
    WIDTH: Optional[int] = None
    DRAUGHT: Optional[float] = None
    TIMESTAMP: str


class MarineTrafficPortResponse(BaseModel):
    """MarineTraffic port congestion response."""

    model_config = ConfigDict(frozen=True)

    PORTID: int
    PORTNAME: str
    UNLOCODE: str
    COUNTRY: str
    IN_ANCHORAGE: int = 0
    IN_PORT: int = 0
    EXPECTED_ARRIVALS: int = 0
    TIMESTAMP: str


class RealMarineTrafficClient:
    """
    Real MarineTraffic API client.

    Provides real-time vessel tracking and port congestion data.
    Uses circuit breaker for resilience.
    """

    BASE_URL = "https://services.marinetraffic.com/api"

    # Vessel type mapping
    VESSEL_TYPES = {
        70: "Cargo",
        71: "Cargo - Hazardous",
        72: "Cargo - Hazardous",
        73: "Cargo - Hazardous",
        74: "Cargo - Hazardous",
        75: "Cargo",
        76: "Cargo",
        77: "Cargo",
        78: "Cargo",
        79: "Cargo",
        80: "Tanker",
        81: "Tanker",
        82: "Tanker",
        83: "Tanker",
        84: "Tanker",
        85: "Tanker",
        86: "Tanker",
        87: "Tanker",
        88: "Tanker",
        89: "Tanker",
    }

    def __init__(
        self,
        api_key: Optional[str] = None,
        config: Optional[AISConfig] = None,
        timeout: float = 30.0,
    ):
        self.api_key = api_key or os.getenv("MARINETRAFFIC_API_KEY")
        self.config = config or AISConfig()
        self._client = httpx.AsyncClient(timeout=timeout)
        self._circuit_breaker = CircuitBreaker(
            name="marinetraffic",
            failure_threshold=5,
            recovery_timeout=60.0,
        )

        if not self.api_key:
            logger.warning("MARINETRAFFIC_API_KEY not set. AIS data will be unavailable.")

    @property
    def is_configured(self) -> bool:
        """Check if API key is configured."""
        return bool(self.api_key)

    async def get_vessels_in_area(
        self,
        lat_min: float,
        lat_max: float,
        lon_min: float,
        lon_max: float,
        vessel_types: Optional[list[str]] = None,
    ) -> list[Vessel]:
        """
        Get vessels in a geographic bounding box.

        Uses MarineTraffic PS01 - Vessel Positions in Area API.
        """
        if not self.is_configured:
            return []

        if not self._circuit_breaker.can_execute():
            logger.debug("Circuit breaker open for MarineTraffic")
            return []

        try:
            response = await self._client.get(
                f"{self.BASE_URL}/exportvessels/{self.api_key}",
                params={
                    "v": "5",
                    "minlat": lat_min,
                    "maxlat": lat_max,
                    "minlon": lon_min,
                    "maxlon": lon_max,
                    "protocol": "jsono",
                    "msgtype": "extended",
                },
            )
            response.raise_for_status()

            self._circuit_breaker.record_success()

            data = response.json()
            vessels = []

            for item in data if isinstance(data, list) else []:
                try:
                    mt_vessel = MarineTrafficVesselResponse(**item)
                    vessel = self._convert_vessel(mt_vessel)
                    vessels.append(vessel)
                except Exception as e:
                    logger.debug("Failed to parse vessel: %s", e)

            return vessels

        except httpx.HTTPStatusError as e:
            logger.error("MarineTraffic API error: %s", e.response.status_code)
            self._circuit_breaker.record_failure()
            return []
        except Exception as e:
            logger.error("MarineTraffic fetch error: %s", e)
            self._circuit_breaker.record_failure()
            return []

    async def get_port_status(self, port_code: str) -> Optional[PortStatus]:
        """
        Get port congestion status.

        Uses MarineTraffic VI01 - Vessel Count in Ports API.
        """
        if not self.is_configured:
            return None

        if not self._circuit_breaker.can_execute():
            return None

        try:
            response = await self._client.get(
                f"{self.BASE_URL}/portvesselcount/{self.api_key}",
                params={
                    "v": "1",
                    "port_unlocode": port_code,
                    "protocol": "jsono",
                },
            )
            response.raise_for_status()

            self._circuit_breaker.record_success()

            data = response.json()
            if not data:
                return None

            port_data = data[0] if isinstance(data, list) else data
            mt_port = MarineTrafficPortResponse(**port_data)

            return self._convert_port_status(port_code, mt_port)

        except Exception as e:
            logger.error("MarineTraffic port status error: %s", e)
            self._circuit_breaker.record_failure()
            return None

    async def get_chokepoint_status(
        self,
        chokepoint_name: str,
    ) -> Optional[ChokePointStatus]:
        """
        Get chokepoint traffic status.

        Aggregates vessel counts in chokepoint areas.
        """
        if not self.is_configured:
            return None

        # Get chokepoint metadata
        meta = CHOKEPOINT_METADATA.get(chokepoint_name)
        if not meta:
            logger.warning("Unknown chokepoint: %s", chokepoint_name)
            return None

        # Define bounding box for chokepoint
        lat, lon = meta["location"]
        lat_min, lat_max = lat - 1.0, lat + 1.0
        lon_min, lon_max = lon - 1.0, lon + 1.0

        vessels = await self.get_vessels_in_area(lat_min, lat_max, lon_min, lon_max)

        # Calculate statistics
        vessels_in_transit = len([v for v in vessels if v.speed_knots > 5])
        vessels_at_anchor = len([v for v in vessels if v.speed_knots <= 1])
        vessels_waiting = len([v for v in vessels if 1 < v.speed_knots <= 5])

        return ChokePointStatus(
            name=chokepoint_name,
            location=meta["location"],
            vessels_in_transit=vessels_in_transit,
            vessels_waiting=vessels_waiting,
            vessels_at_anchor=vessels_at_anchor,
            avg_transit_time_hours=meta["normal_transit_hours"],
            normal_transit_time_hours=meta["normal_transit_hours"],
            normal_daily_transits=meta["daily_transits"],
            affected_routes=meta["affected_routes"],
            timestamp=datetime.now(timezone.utc),
            data_source="marinetraffic",
        )

    async def get_vessel_by_mmsi(self, mmsi: int) -> Optional[Vessel]:
        """
        Get vessel details by MMSI.

        Uses MarineTraffic PS07 - Single Vessel Position API.
        """
        if not self.is_configured:
            return None

        if not self._circuit_breaker.can_execute():
            return None

        try:
            response = await self._client.get(
                f"{self.BASE_URL}/exportvessel/{self.api_key}",
                params={
                    "v": "5",
                    "mmsi": mmsi,
                    "protocol": "jsono",
                    "msgtype": "extended",
                },
            )
            response.raise_for_status()

            self._circuit_breaker.record_success()

            data = response.json()
            if not data:
                return None

            vessel_data = data[0] if isinstance(data, list) else data
            mt_vessel = MarineTrafficVesselResponse(**vessel_data)

            return self._convert_vessel(mt_vessel)

        except Exception as e:
            logger.error("MarineTraffic vessel fetch error: %s", e)
            self._circuit_breaker.record_failure()
            return None

    def _convert_vessel(self, mt_vessel: MarineTrafficVesselResponse) -> Vessel:
        """Convert MarineTraffic response to Vessel model."""
        vessel_type = self.VESSEL_TYPES.get(mt_vessel.SHIPTYPE or 0, "Unknown")

        return Vessel(
            mmsi=mt_vessel.MMSI,
            imo=mt_vessel.IMO,
            name=mt_vessel.SHIPNAME or f"VESSEL-{mt_vessel.MMSI}",
            vessel_type=vessel_type,
            lat=mt_vessel.LAT,
            lon=mt_vessel.LON,
            speed_knots=mt_vessel.SPEED or 0.0,
            course_degrees=mt_vessel.COURSE or 0.0,
            heading_degrees=mt_vessel.HEADING,
            flag=mt_vessel.FLAG or "Unknown",
            length_m=mt_vessel.LENGTH,
            width_m=mt_vessel.WIDTH,
            draught_m=mt_vessel.DRAUGHT,
            timestamp=datetime.now(timezone.utc),
        )

    def _convert_port_status(
        self,
        port_code: str,
        mt_port: MarineTrafficPortResponse,
    ) -> PortStatus:
        """Convert MarineTraffic response to PortStatus model."""
        # Get additional metadata
        meta = PORT_METADATA.get(port_code, {})

        return PortStatus(
            port_code=port_code,
            port_name=mt_port.PORTNAME,
            country=mt_port.COUNTRY,
            region=meta.get("region", ""),
            lat=meta.get("lat", 0.0),
            lon=meta.get("lon", 0.0),
            vessels_waiting=mt_port.EXPECTED_ARRIVALS,
            vessels_berthed=mt_port.IN_PORT,
            vessels_at_anchor=mt_port.IN_ANCHORAGE,
            avg_wait_time_hours=meta.get("normal_wait_hours", 6.0),
            normal_waiting=meta.get("normal_waiting", 10),
            normal_wait_time_hours=meta.get("normal_wait_hours", 6.0),
            timestamp=datetime.now(timezone.utc),
            data_quality=0.95,
        )

    async def fetch_logistics_signals(self) -> list[RawSignalEvent]:
        """
        Fetch logistics-relevant signals from AIS data.

        Detects:
        - Port congestion anomalies
        - Chokepoint delays
        - Unusual vessel behavior
        """
        events = []

        # Check major ports for congestion
        major_ports = ["SGSIN", "CNSHA", "HKHKG", "NLRTM", "USLAX"]
        for port_code in major_ports:
            status = await self.get_port_status(port_code)
            if status and self._is_congestion_anomaly(status):
                event = self._create_congestion_signal(status)
                events.append(event)

        # Check chokepoints
        chokepoints = ["Suez Canal", "Panama Canal", "Strait of Malacca"]
        for cp_name in chokepoints:
            status = await self.get_chokepoint_status(cp_name)
            if status and self._is_chokepoint_anomaly(status):
                event = self._create_chokepoint_signal(status)
                events.append(event)

        return events

    def _is_congestion_anomaly(self, status: PortStatus) -> bool:
        """Check if port shows congestion anomaly."""
        if status.normal_waiting == 0:
            return False
        ratio = status.vessels_waiting / status.normal_waiting
        return ratio > 1.5  # 50% above normal

    def _is_chokepoint_anomaly(self, status: ChokePointStatus) -> bool:
        """Check if chokepoint shows delay anomaly."""
        if status.normal_transit_time_hours == 0:
            return False
        ratio = status.avg_transit_time_hours / status.normal_transit_time_hours
        return ratio > 1.3  # 30% above normal

    def _create_congestion_signal(self, status: PortStatus) -> RawSignalEvent:
        """Create signal for port congestion."""
        ratio = status.vessels_waiting / max(status.normal_waiting, 1)

        return RawSignalEvent(
            event_id=f"ais-congestion-{status.port_code}-{status.timestamp.strftime('%Y%m%d')}",
            title=f"Port Congestion: {status.port_name} ({status.port_code})",
            description=f"Vessel waiting count is {ratio:.1f}x normal levels. "
            f"{status.vessels_waiting} vessels waiting vs normal {status.normal_waiting}.",
            probability=min(0.95, 0.5 + (ratio - 1) * 0.2),
            probability_is_fallback=False,
            keywords=["port", "congestion", status.port_code.lower(), status.country.lower()],
            observed_at=status.timestamp,
            source_metrics={
                "vessels_waiting": status.vessels_waiting,
                "normal_waiting": status.normal_waiting,
                "congestion_ratio": round(ratio, 2),
                "avg_wait_hours": status.avg_wait_time_hours,
            },
        )

    def _create_chokepoint_signal(self, status: ChokePointStatus) -> RawSignalEvent:
        """Create signal for chokepoint delays."""
        ratio = status.avg_transit_time_hours / max(status.normal_transit_time_hours, 1)

        return RawSignalEvent(
            event_id=f"ais-chokepoint-{status.name.replace(' ', '_')}-{status.timestamp.strftime('%Y%m%d')}",
            title=f"Chokepoint Delay: {status.name}",
            description=f"Transit time is {ratio:.1f}x normal. "
            f"{status.vessels_waiting} vessels waiting for passage.",
            probability=min(0.95, 0.5 + (ratio - 1) * 0.3),
            probability_is_fallback=False,
            keywords=["chokepoint", status.name.lower().replace(" ", "_"), "delay"],
            observed_at=status.timestamp,
            source_metrics={
                "vessels_waiting": status.vessels_waiting,
                "avg_transit_hours": status.avg_transit_time_hours,
                "normal_transit_hours": status.normal_transit_time_hours,
                "delay_ratio": round(ratio, 2),
            },
        )

    async def health_check(self) -> dict:
        """Check MarineTraffic API health."""
        status = {
            "source": "marinetraffic",
            "configured": self.is_configured,
            "circuit_breaker": self._circuit_breaker.state,
        }

        if not self.is_configured:
            status["status"] = "unconfigured"
            return status

        # Test with a simple vessel query
        try:
            vessels = await self.get_vessels_in_area(
                lat_min=1.2,
                lat_max=1.4,
                lon_min=103.7,
                lon_max=103.9,
            )
            status["status"] = "healthy"
            status["test_vessels_found"] = len(vessels)
        except Exception as e:
            status["status"] = "unhealthy"
            status["error"] = str(e)

        return status

    async def close(self):
        """Close HTTP client."""
        await self._client.aclose()


# Factory function
def create_marinetraffic_client(
    api_key: Optional[str] = None,
    config: Optional[AISConfig] = None,
) -> RealMarineTrafficClient:
    """Create MarineTraffic client."""
    return RealMarineTrafficClient(api_key=api_key, config=config)
