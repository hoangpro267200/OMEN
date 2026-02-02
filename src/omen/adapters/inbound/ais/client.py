"""
AIS API clients.

Provides clients for different AIS data providers:
- AISHub (free, limited)
- MarineTraffic (paid, comprehensive)
- Mock (for testing/demo)
"""

import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Iterator
import random

from .schemas import Vessel, PortStatus, ChokePointStatus
from .config import AISConfig, PORT_METADATA, CHOKEPOINT_METADATA

logger = logging.getLogger(__name__)


class AISClient(ABC):
    """Abstract base class for AIS clients."""

    @abstractmethod
    def get_vessels_in_area(
        self,
        lat_min: float,
        lat_max: float,
        lon_min: float,
        lon_max: float,
        vessel_types: list[str] | None = None,
    ) -> list[Vessel]:
        """Get vessels in a geographic bounding box."""
        pass

    @abstractmethod
    def get_port_status(self, port_code: str) -> PortStatus:
        """Get congestion status for a specific port."""
        pass

    @abstractmethod
    def get_chokepoint_status(self, chokepoint_name: str) -> ChokePointStatus:
        """Get status of a shipping chokepoint."""
        pass

    @abstractmethod
    def get_vessel_by_mmsi(self, mmsi: int) -> Vessel | None:
        """Get vessel details by MMSI."""
        pass


class MockAISClient(AISClient):
    """
    Mock AIS client for testing and demo.

    Generates realistic but synthetic AIS data.
    """

    def __init__(
        self,
        config: AISConfig | None = None,
        scenario: str = "normal",
    ):
        """
        Initialize mock client.

        Args:
            config: AIS configuration
            scenario: Scenario to simulate
                - "normal": Normal operations
                - "congestion": Port congestion at major ports
                - "suez_delay": Suez Canal delays
                - "multi_crisis": Multiple simultaneous issues
        """
        self.config = config or AISConfig()
        self.scenario = scenario

    def get_vessels_in_area(
        self,
        lat_min: float,
        lat_max: float,
        lon_min: float,
        lon_max: float,
        vessel_types: list[str] | None = None,
    ) -> list[Vessel]:
        """Generate mock vessels in area."""
        now = datetime.now(timezone.utc)
        vessels = []

        # Generate 5-20 vessels
        count = random.randint(5, 20)
        for i in range(count):
            vessel = Vessel(
                mmsi=200000000 + random.randint(1, 999999999),
                imo=9000000 + random.randint(1, 999999),
                name=f"MOCK VESSEL {i+1}",
                vessel_type=random.choice(["Container Ship", "Tanker", "Bulk Carrier"]),
                lat=random.uniform(lat_min, lat_max),
                lon=random.uniform(lon_min, lon_max),
                speed_knots=random.uniform(0, 20),
                course_degrees=random.uniform(0, 360),
                flag=random.choice(["PA", "LR", "MH", "HK", "SG"]),
                length_m=random.randint(100, 400),
                width_m=random.randint(20, 60),
                draught_m=random.uniform(8, 16),
                timestamp=now,
            )
            vessels.append(vessel)

        return vessels

    def get_port_status(self, port_code: str) -> PortStatus:
        """Generate mock port status based on scenario."""
        now = datetime.now(timezone.utc)

        # Get port metadata or use defaults
        meta = PORT_METADATA.get(port_code, {
            "name": port_code,
            "country": "Unknown",
            "region": "Unknown",
            "lat": 0.0,
            "lon": 0.0,
            "normal_waiting": 10,
            "normal_wait_hours": 6.0,
        })

        normal_waiting = meta["normal_waiting"]
        normal_wait_hours = meta["normal_wait_hours"]

        # Calculate current values based on scenario
        if self.scenario == "normal":
            # Normal: 80-120% of baseline
            multiplier = random.uniform(0.8, 1.2)
        elif self.scenario == "congestion":
            # Congestion at specific ports
            if port_code in ["SGSIN", "CNSHA", "USLAX", "USLGB"]:
                multiplier = random.uniform(2.0, 3.5)  # 200-350% congestion
            else:
                multiplier = random.uniform(0.9, 1.3)
        elif self.scenario == "suez_delay":
            # Suez impacts Europe-bound ports
            if port_code in ["NLRTM", "DEHAM", "BEANR"]:
                multiplier = random.uniform(1.5, 2.5)
            else:
                multiplier = random.uniform(0.9, 1.2)
        elif self.scenario == "multi_crisis":
            # Random high congestion
            if random.random() < 0.4:
                multiplier = random.uniform(1.8, 4.0)
            else:
                multiplier = random.uniform(0.9, 1.4)
        else:
            multiplier = 1.0

        vessels_waiting = int(normal_waiting * multiplier)
        avg_wait_time = normal_wait_hours * multiplier

        return PortStatus(
            port_code=port_code,
            port_name=meta["name"],
            country=meta["country"],
            region=meta.get("region", ""),
            lat=meta["lat"],
            lon=meta["lon"],
            vessels_waiting=vessels_waiting,
            vessels_berthed=random.randint(5, 20),
            vessels_at_anchor=random.randint(0, 10),
            avg_wait_time_hours=avg_wait_time,
            normal_waiting=normal_waiting,
            normal_wait_time_hours=normal_wait_hours,
            timestamp=now,
            data_quality=0.95,
        )

    def get_chokepoint_status(self, chokepoint_name: str) -> ChokePointStatus:
        """Generate mock chokepoint status based on scenario."""
        now = datetime.now(timezone.utc)

        # Get chokepoint metadata
        meta = CHOKEPOINT_METADATA.get(chokepoint_name, {
            "location": (0.0, 0.0),
            "normal_transit_hours": 12.0,
            "daily_transits": 40,
            "affected_routes": ["Global shipping"],
        })

        normal_transit = meta["normal_transit_hours"]
        daily_transits = meta["daily_transits"]

        # Calculate current values based on scenario
        if self.scenario == "normal":
            delay_multiplier = random.uniform(0.9, 1.2)
            vessels_waiting = random.randint(0, 10)
        elif self.scenario == "suez_delay":
            if chokepoint_name == "Suez Canal":
                delay_multiplier = random.uniform(2.0, 4.0)
                vessels_waiting = random.randint(30, 80)
            elif chokepoint_name == "Cape of Good Hope":
                # Alternative route gets busier
                delay_multiplier = random.uniform(1.2, 1.8)
                vessels_waiting = random.randint(10, 30)
            else:
                delay_multiplier = random.uniform(0.9, 1.3)
                vessels_waiting = random.randint(0, 15)
        elif self.scenario == "multi_crisis":
            if random.random() < 0.3:
                delay_multiplier = random.uniform(1.8, 3.5)
                vessels_waiting = random.randint(20, 60)
            else:
                delay_multiplier = random.uniform(0.9, 1.4)
                vessels_waiting = random.randint(0, 15)
        else:
            delay_multiplier = 1.0
            vessels_waiting = 5

        avg_transit = normal_transit * delay_multiplier

        return ChokePointStatus(
            name=chokepoint_name,
            location=meta["location"],
            vessels_in_transit=random.randint(10, 30),
            vessels_waiting=vessels_waiting,
            vessels_at_anchor=random.randint(0, 20),
            avg_transit_time_hours=avg_transit,
            normal_transit_time_hours=normal_transit,
            normal_daily_transits=daily_transits,
            affected_routes=meta["affected_routes"],
            timestamp=now,
            data_source="mock",
        )

    def get_vessel_by_mmsi(self, mmsi: int) -> Vessel | None:
        """Get mock vessel by MMSI."""
        now = datetime.now(timezone.utc)
        return Vessel(
            mmsi=mmsi,
            imo=9000000 + (mmsi % 1000000),
            name=f"VESSEL {mmsi}",
            vessel_type="Container Ship",
            lat=random.uniform(-60, 60),
            lon=random.uniform(-180, 180),
            speed_knots=random.uniform(10, 20),
            course_degrees=random.uniform(0, 360),
            flag="PA",
            length_m=300,
            width_m=45,
            draught_m=12.0,
            timestamp=now,
        )


class MarineTrafficClient(AISClient):
    """
    MarineTraffic API client (paid service).

    Requires API key from marinetraffic.com
    """

    def __init__(self, config: AISConfig):
        self.config = config
        self.base_url = config.marinetraffic_base_url
        self.api_key = config.marinetraffic_api_key

        if not self.api_key:
            raise ValueError("MarineTraffic API key is required")

    def get_vessels_in_area(
        self,
        lat_min: float,
        lat_max: float,
        lon_min: float,
        lon_max: float,
        vessel_types: list[str] | None = None,
    ) -> list[Vessel]:
        """Get vessels from MarineTraffic API."""
        # TODO: Implement actual API call
        # For now, fall back to mock
        logger.warning("MarineTraffic API not implemented, using mock data")
        mock = MockAISClient(self.config)
        return mock.get_vessels_in_area(lat_min, lat_max, lon_min, lon_max, vessel_types)

    def get_port_status(self, port_code: str) -> PortStatus:
        """Get port status from MarineTraffic API."""
        # TODO: Implement actual API call
        logger.warning("MarineTraffic API not implemented, using mock data")
        mock = MockAISClient(self.config)
        return mock.get_port_status(port_code)

    def get_chokepoint_status(self, chokepoint_name: str) -> ChokePointStatus:
        """Get chokepoint status from MarineTraffic API."""
        # TODO: Implement actual API call
        logger.warning("MarineTraffic API not implemented, using mock data")
        mock = MockAISClient(self.config)
        return mock.get_chokepoint_status(chokepoint_name)

    def get_vessel_by_mmsi(self, mmsi: int) -> Vessel | None:
        """Get vessel from MarineTraffic API."""
        # TODO: Implement actual API call
        logger.warning("MarineTraffic API not implemented, using mock data")
        mock = MockAISClient(self.config)
        return mock.get_vessel_by_mmsi(mmsi)


def create_ais_client(config: AISConfig) -> AISClient:
    """
    Factory function to create appropriate AIS client.

    Args:
        config: AIS configuration

    Returns:
        AISClient instance based on provider setting
    """
    provider = config.provider

    if provider == "mock":
        return MockAISClient(config, scenario="normal")
    elif provider == "marinetraffic":
        return MarineTrafficClient(config)
    elif provider == "aishub":
        # TODO: Implement AISHub client
        logger.warning("AISHub client not implemented, using mock")
        return MockAISClient(config)
    elif provider == "vesselfinder":
        # TODO: Implement VesselFinder client
        logger.warning("VesselFinder client not implemented, using mock")
        return MockAISClient(config)
    else:
        logger.warning(f"Unknown provider {provider}, using mock")
        return MockAISClient(config)
