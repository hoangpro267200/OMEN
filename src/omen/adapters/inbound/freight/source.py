"""
Freight Signal Source.
"""

import logging
import random
from datetime import datetime, timezone
from typing import Iterator, AsyncIterator

from omen.application.ports.signal_source import SignalSource
from omen.domain.models.raw_signal import RawSignalEvent
from .schemas import FreightRate, FreightIndex, RouteCapacity
from .mapper import FreightMapper
from .config import FreightConfig, ROUTE_METADATA

logger = logging.getLogger(__name__)


class FreightSignalSource(SignalSource):
    """Freight rates data source for OMEN."""

    def __init__(
        self,
        mapper: FreightMapper | None = None,
        config: FreightConfig | None = None,
    ):
        self._config = config or FreightConfig()
        self._mapper = mapper or FreightMapper(self._config)

    @property
    def source_name(self) -> str:
        return "freight"

    def fetch_events(self, limit: int = 100) -> Iterator[RawSignalEvent]:
        """Fetch freight rate events."""
        events: list[RawSignalEvent] = []

        # Fetch route rates
        for route in self._config.monitored_routes:
            try:
                rate = self._fetch_route_rate(route)
                event = self._mapper.map_rate_spike(rate)
                if event:
                    events.append(event)
            except Exception as e:
                logger.error(f"Failed to fetch rate for {route}: {e}")

        # Fetch global indices
        for index_name in ["FBX", "SCFI"]:
            try:
                index = self._fetch_index(index_name)
                event = self._mapper.map_index_change(index)
                if event:
                    events.append(event)
            except Exception as e:
                logger.error(f"Failed to fetch index {index_name}: {e}")

        logger.info(f"Freight source found {len(events)} events")

        for event in events[:limit]:
            yield event

    async def fetch_events_async(self, limit: int = 100) -> AsyncIterator[RawSignalEvent]:
        """Async version."""
        for event in self.fetch_events(limit):
            yield event

    def fetch_by_id(self, market_id: str) -> RawSignalEvent | None:
        """Fetch specific freight data."""
        if market_id in ROUTE_METADATA:
            rate = self._fetch_route_rate(market_id)
            return self._mapper.map_rate_spike(rate)
        return None

    def _fetch_route_rate(self, route: str) -> FreightRate:
        """Fetch rate for a specific route."""
        return self._generate_mock_rate(route)

    def _fetch_index(self, index_name: str) -> FreightIndex:
        """Fetch freight index."""
        return self._generate_mock_index(index_name)

    def _generate_mock_rate(self, route: str) -> FreightRate:
        """Generate mock freight rate data."""
        now = datetime.now(timezone.utc)
        meta = ROUTE_METADATA.get(route, {})

        baseline = meta.get("baseline_rate_usd", 2000)

        # Simulate rate variations
        volatility = random.uniform(-0.3, 0.5)  # -30% to +50%
        current_rate = baseline * (1 + volatility)

        # Historical rates
        rate_7d_ago = baseline * (1 + random.uniform(-0.2, 0.3))
        rate_30d_ago = baseline * (1 + random.uniform(-0.15, 0.25))

        change_7d = ((current_rate - rate_7d_ago) / rate_7d_ago) * 100
        change_30d = ((current_rate - rate_30d_ago) / rate_30d_ago) * 100

        # Detect spikes
        is_spike = abs(change_7d) > self._config.spike_threshold_pct
        spike_severity = "none"
        if is_spike:
            if abs(change_7d) > 50:
                spike_severity = "extreme"
            elif abs(change_7d) > 40:
                spike_severity = "high"
            elif abs(change_7d) > 30:
                spike_severity = "medium"
            else:
                spike_severity = "low"

        return FreightRate(
            route=route,
            origin_port=meta.get("origin", "Unknown"),
            origin_code=meta.get("origin_code", ""),
            destination_port=meta.get("destination", "Unknown"),
            destination_code=meta.get("destination_code", ""),
            rate_usd_per_feu=current_rate,
            rate_usd_per_teu=current_rate * 0.55,
            rate_7d_ago=rate_7d_ago,
            rate_30d_ago=rate_30d_ago,
            change_7d_pct=change_7d,
            change_30d_pct=change_30d,
            capacity_utilization_pct=random.uniform(70, 98),
            booking_volume_index=random.uniform(80, 130),
            blank_sailings=random.randint(0, 3) if random.random() < 0.3 else 0,
            is_spike=is_spike,
            spike_severity=spike_severity,
            timestamp=now,
        )

    def _generate_mock_index(self, index_name: str) -> FreightIndex:
        """Generate mock freight index."""
        now = datetime.now(timezone.utc)

        # Base values for indices
        base_values = {
            "FBX": 2500,
            "SCFI": 1800,
            "WCI": 3000,
        }
        base = base_values.get(index_name, 2000)

        current = base * random.uniform(0.8, 1.5)

        return FreightIndex(
            index_name=index_name,
            index_value=current,
            change_7d_pct=random.uniform(-15, 20),
            change_30d_pct=random.uniform(-25, 35),
            change_ytd_pct=random.uniform(-30, 50),
            value_52w_high=current * 1.3,
            value_52w_low=current * 0.6,
            timestamp=now,
        )


class MockFreightSignalSource(FreightSignalSource):
    """Mock freight source with configurable scenarios."""

    def __init__(
        self,
        scenario: str = "normal",
        config: FreightConfig | None = None,
    ):
        super().__init__(config=config)
        self._scenario = scenario

    def _generate_mock_rate(self, route: str) -> FreightRate:
        """Generate rate based on scenario."""
        rate = super()._generate_mock_rate(route)

        if self._scenario == "spike":
            # Force a spike on key routes
            if route in ["SHA-LAX", "SHA-RTM"]:
                rate.change_7d_pct = random.uniform(30, 50)
                rate.is_spike = True
                rate.spike_severity = "high"
                rate.rate_usd_per_feu = rate.rate_7d_ago * 1.4

        elif self._scenario == "capacity_crisis":
            rate.capacity_utilization_pct = random.uniform(95, 100)
            rate.blank_sailings = random.randint(2, 5)
            rate.change_7d_pct = random.uniform(20, 40)
            rate.is_spike = True

        return rate


def create_freight_source(
    config: FreightConfig | None = None,
    scenario: str | None = None,
) -> FreightSignalSource:
    """Factory function to create freight source."""
    config = config or FreightConfig()

    if scenario:
        return MockFreightSignalSource(scenario=scenario, config=config)

    return FreightSignalSource(config=config)
