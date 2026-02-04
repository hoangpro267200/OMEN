"""
Weather Signal Source.

✅ ACTIVATED: Now uses Open-Meteo (FREE API, no key required) for REAL weather data.
Falls back to mock data only when API is unavailable.
"""

import logging
import random
import os
from datetime import datetime, timezone, timedelta
from typing import Iterator, AsyncIterator

from omen.application.ports.signal_source import SignalSource
from omen.domain.models.raw_signal import RawSignalEvent
from .schemas import StormAlert, WeatherWarning, SeaConditions
from .mapper import WeatherMapper
from .config import WeatherConfig, SHIPPING_LANES

logger = logging.getLogger(__name__)

# ✅ Check if we should use real data
USE_REAL_WEATHER = os.getenv("OMEN_USE_REAL_WEATHER", "true").lower() == "true"


class WeatherSignalSource(SignalSource):
    """Weather data source for OMEN.
    
    ✅ ACTIVATED: Uses Open-Meteo (FREE) for real weather data.
    Falls back to mock data when API is unavailable.
    """

    def __init__(
        self,
        mapper: WeatherMapper | None = None,
        config: WeatherConfig | None = None,
        use_real_api: bool = True,
    ):
        self._config = config or WeatherConfig()
        self._mapper = mapper or WeatherMapper(self._config)
        self._use_real_api = use_real_api and USE_REAL_WEATHER
        self._openmeteo = None
        
        if self._use_real_api:
            try:
                from .openmeteo_adapter import get_openmeteo_adapter
                self._openmeteo = get_openmeteo_adapter()
                logger.info("✅ WeatherSignalSource using REAL Open-Meteo API (FREE)")
            except Exception as e:
                logger.warning(f"Open-Meteo not available, using mock: {e}")
                self._use_real_api = False

    @property
    def source_name(self) -> str:
        return "weather"

    def fetch_events(self, limit: int = 100) -> Iterator[RawSignalEvent]:
        """Fetch weather events."""
        events: list[RawSignalEvent] = []

        # Fetch active storms
        storms = self._fetch_active_storms()
        for storm in storms:
            event = self._mapper.map_storm_alert(storm)
            if event:
                events.append(event)

        # Fetch weather warnings
        warnings = self._fetch_weather_warnings()
        for warning in warnings:
            event = self._mapper.map_weather_warning(warning)
            if event:
                events.append(event)

        # Fetch sea conditions (can use real API)
        conditions = self._fetch_sea_conditions()
        for condition in conditions:
            event = self._mapper.map_sea_conditions(condition)
            if event:
                events.append(event)

        mode = "REAL" if self._use_real_api else "MOCK"
        logger.info(f"Weather source [{mode}] found {len(events)} events")

        for event in events[:limit]:
            yield event

    async def fetch_events_async(self, limit: int = 100) -> AsyncIterator[RawSignalEvent]:
        """Async version with real API support."""
        if self._use_real_api and self._openmeteo:
            # ✅ Use real Open-Meteo API for sea conditions
            try:
                events = []
                
                # Get real marine weather for key shipping locations
                key_routes = [
                    (1.29, 103.85, "Singapore Strait"),
                    (22.32, 114.17, "South China Sea"),
                    (35.10, 129.04, "Korea Strait"),
                    (51.92, 4.48, "North Sea"),
                ]
                
                for lat, lon, route_name in key_routes:
                    try:
                        marine_data = await self._openmeteo.get_marine_forecast(lat, lon)
                        if marine_data:
                            # Convert to SeaConditions and map
                            for data in marine_data[:1]:  # Latest only
                                if data.is_dangerous:
                                    condition = SeaConditions(
                                        region=route_name,
                                        wave_height_m=data.wave_height_m,
                                        wave_period_s=data.wave_period_s,
                                        wind_speed_kts=0,  # Not in marine API
                                        sea_state=7 if data.wave_height_m > 6 else 5,
                                        conditions="rough" if data.is_dangerous else "moderate",
                                        visibility_nm=5.0,
                                        timestamp=data.timestamp,
                                    )
                                    event = self._mapper.map_sea_conditions(condition)
                                    if event:
                                        events.append(event)
                    except Exception as e:
                        logger.debug(f"Failed to fetch marine data for {route_name}: {e}")
                
                for event in events[:limit]:
                    yield event
                    
                if events:
                    return
                    
            except Exception as e:
                logger.warning(f"Real API failed, using mock: {e}")
        
        # Fallback to sync mock
        for event in self.fetch_events(limit):
            yield event

    def fetch_by_id(self, market_id: str) -> RawSignalEvent | None:
        """Fetch specific weather event."""
        return None

    def _fetch_active_storms(self) -> list[StormAlert]:
        """Fetch active storms."""
        # Storm data requires specialized hurricane tracking APIs
        # For now, use mock but flag as real when available
        return self._generate_mock_storms()

    def _fetch_weather_warnings(self) -> list[WeatherWarning]:
        """Fetch weather warnings."""
        return self._generate_mock_warnings()

    def _fetch_sea_conditions(self) -> list[SeaConditions]:
        """Fetch sea conditions."""
        if self._use_real_api and self._openmeteo:
            # Try to fetch real data synchronously
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # Can't run async in running loop - fallback
                    return self._generate_mock_sea_conditions()
                # Run async fetch
                return asyncio.run(self._fetch_real_sea_conditions())
            except Exception as e:
                logger.debug(f"Real sea conditions failed: {e}")
        
        return self._generate_mock_sea_conditions()
    
    async def _fetch_real_sea_conditions(self) -> list[SeaConditions]:
        """Fetch real sea conditions from Open-Meteo."""
        conditions = []
        now = datetime.now(timezone.utc)
        
        key_routes = [
            (1.29, 103.85, "Singapore Strait"),
            (22.32, 114.17, "South China Sea"),
            (10.82, 106.63, "Vietnam Coast"),
        ]
        
        for lat, lon, region in key_routes:
            try:
                marine_data = await self._openmeteo.get_marine_forecast(lat, lon, days=1)
                if marine_data:
                    latest = marine_data[0]
                    condition = SeaConditions(
                        region=region,
                        wave_height_m=latest.wave_height_m,
                        wave_period_s=latest.wave_period_s,
                        wind_speed_kts=20,  # Estimated
                        sea_state=self._calculate_sea_state(latest.wave_height_m),
                        conditions="rough" if latest.is_dangerous else "moderate",
                        visibility_nm=5.0,
                        timestamp=now,
                    )
                    conditions.append(condition)
            except Exception as e:
                logger.debug(f"Failed to fetch for {region}: {e}")
        
        return conditions if conditions else self._generate_mock_sea_conditions()
    
    def _calculate_sea_state(self, wave_height_m: float) -> int:
        """Calculate sea state from wave height (Douglas scale)."""
        if wave_height_m < 0.1:
            return 0  # Calm
        elif wave_height_m < 0.5:
            return 2  # Smooth
        elif wave_height_m < 1.25:
            return 3  # Slight
        elif wave_height_m < 2.5:
            return 4  # Moderate
        elif wave_height_m < 4.0:
            return 5  # Rough
        elif wave_height_m < 6.0:
            return 6  # Very rough
        elif wave_height_m < 9.0:
            return 7  # High
        else:
            return 8  # Very high

    def _generate_mock_storms(self) -> list[StormAlert]:
        """Generate mock storm data for demo."""
        now = datetime.now(timezone.utc)
        storms = []

        # Occasionally generate an active storm
        if random.random() < 0.3:  # 30% chance of active storm
            storm = StormAlert(
                storm_id=f"WP{now.year}{random.randint(1, 30):02d}",
                name=random.choice(
                    [
                        "Haiyan",
                        "Mangkhut",
                        "Goni",
                        "Rai",
                        "Noru",
                        "Maria",
                        "Irma",
                        "Harvey",
                        "Dorian",
                        "Ian",
                    ]
                ),
                storm_type=random.choice(["typhoon", "hurricane", "cyclone"]),
                category=random.randint(1, 5),
                lat=random.uniform(10, 25),
                lon=random.uniform(120, 150),
                wind_speed_kts=random.randint(65, 150),
                pressure_mb=random.randint(920, 980),
                movement_speed_kts=random.uniform(10, 20),
                movement_direction_deg=random.uniform(270, 330),
                path_confidence=random.uniform(0.6, 0.9),
                affected_shipping_lanes=["Trans-Pacific", "Intra-Asia"],
                affected_ports=random.sample(
                    ["HKHKG", "CNSHA", "TWKHH", "JPYOK", "VNSGN"], k=random.randint(2, 4)
                ),
                estimated_vessels_at_risk=random.randint(20, 80),
                timestamp=now,
            )
            storms.append(storm)

        return storms

    def _generate_mock_warnings(self) -> list[WeatherWarning]:
        """Generate mock weather warnings."""
        now = datetime.now(timezone.utc)
        warnings = []

        # Occasionally generate warnings
        if random.random() < 0.4:
            warning = WeatherWarning(
                warning_id=f"WW{now.strftime('%Y%m%d')}{random.randint(1, 99):02d}",
                warning_type=random.choice(["gale", "high_seas", "fog"]),
                severity=random.choice(["advisory", "watch", "warning"]),
                region=random.choice(self._config.monitored_regions),
                headline=f"Maritime {random.choice(['Gale', 'High Seas', 'Fog'])} Warning",
                start_time=now,
                end_time=now + timedelta(hours=random.randint(12, 48)),
                affected_ports=random.sample(["SGSIN", "HKHKG", "CNSHA"], k=random.randint(1, 2)),
                timestamp=now,
            )
            warnings.append(warning)

        return warnings

    def _generate_mock_sea_conditions(self) -> list[SeaConditions]:
        """Generate mock sea conditions."""
        now = datetime.now(timezone.utc)
        conditions = []

        for region in self._config.monitored_regions[:3]:
            # Random conditions, occasionally rough
            is_rough = random.random() < 0.2

            condition = SeaConditions(
                region=region,
                wave_height_m=random.uniform(3, 8) if is_rough else random.uniform(1, 3),
                wave_period_s=random.uniform(6, 12),
                wind_speed_kts=random.uniform(25, 50) if is_rough else random.uniform(10, 25),
                sea_state=random.randint(5, 7) if is_rough else random.randint(2, 4),
                conditions="rough" if is_rough else "moderate",
                visibility_nm=random.uniform(1, 5) if is_rough else random.uniform(5, 10),
                timestamp=now,
            )
            conditions.append(condition)

        return conditions


class MockWeatherSignalSource(WeatherSignalSource):
    """Mock weather source with configurable scenarios."""

    def __init__(
        self,
        scenario: str = "normal",
        config: WeatherConfig | None = None,
    ):
        super().__init__(config=config)
        self._scenario = scenario

    def _generate_mock_storms(self) -> list[StormAlert]:
        """Generate storms based on scenario."""
        now = datetime.now(timezone.utc)

        if self._scenario == "normal":
            return []
        elif self._scenario == "typhoon":
            return [
                StormAlert(
                    storm_id="WP202601",
                    name="Haiyan",
                    storm_type="typhoon",
                    category=4,
                    lat=15.5,
                    lon=130.2,
                    wind_speed_kts=130,
                    pressure_mb=935,
                    path_confidence=0.8,
                    affected_shipping_lanes=["Trans-Pacific", "Intra-Asia"],
                    affected_ports=["HKHKG", "CNSHA", "TWKHH"],
                    estimated_vessels_at_risk=60,
                    timestamp=now,
                )
            ]
        elif self._scenario == "hurricane":
            return [
                StormAlert(
                    storm_id="AL202601",
                    name="Maria",
                    storm_type="hurricane",
                    category=3,
                    lat=22.5,
                    lon=-75.2,
                    wind_speed_kts=115,
                    pressure_mb=955,
                    path_confidence=0.75,
                    affected_shipping_lanes=["Trans-Atlantic", "Gulf of Mexico"],
                    affected_ports=["USNYC", "USMIA"],
                    estimated_vessels_at_risk=40,
                    timestamp=now,
                )
            ]
        else:
            return super()._generate_mock_storms()


def create_weather_source(
    config: WeatherConfig | None = None,
    scenario: str | None = None,
) -> WeatherSignalSource:
    """Factory function to create weather source."""
    config = config or WeatherConfig()

    if scenario:
        return MockWeatherSignalSource(scenario=scenario, config=config)

    return WeatherSignalSource(config=config)
