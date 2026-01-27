"""Stub Signal Source for testing.

Provides predictable, reproducible test data.
"""

from datetime import datetime, timedelta
from typing import AsyncIterator, Iterator

from ...domain.models.raw_signal import RawSignalEvent, MarketMetadata
from ...domain.models.common import GeoLocation, ProbabilityMovement, MarketId, EventId
from ...application.ports.signal_source import SignalSource


class StubSignalSource(SignalSource):
    """
    In-memory stub for testing without external API calls.
    
    Provides deterministic test events for reproducible tests.
    """
    
    def __init__(self, events: list[RawSignalEvent] | None = None):
        self._events = events or self._generate_default_events()
    
    @property
    def source_name(self) -> str:
        return "stub"
    
    def fetch_events(self, limit: int = 100) -> Iterator[RawSignalEvent]:
        for event in self._events[:limit]:
            yield event
    
    async def fetch_events_async(self, limit: int = 100) -> AsyncIterator[RawSignalEvent]:
        for event in self._events[:limit]:
            yield event
    
    def fetch_by_id(self, market_id: str) -> RawSignalEvent | None:
        for event in self._events:
            if event.market.market_id == market_id:
                return event
        return None
    
    def add_event(self, event: RawSignalEvent) -> None:
        """Add an event for testing."""
        self._events.append(event)
    
    @staticmethod
    def _generate_default_events() -> list[RawSignalEvent]:
        """Generate deterministic test events."""
        return [
            # High-confidence Red Sea disruption event
            RawSignalEvent(
                event_id=EventId("test-red-sea-001"),
                title="Red Sea shipping disruption due to Houthi attacks",
                description="Will commercial shipping through the Red Sea be significantly disrupted by January 2024?",
                probability=0.75,
                movement=ProbabilityMovement(
                    current=0.75,
                    previous=0.60,
                    delta=0.15,
                    window_hours=24
                ),
                keywords=["red sea", "shipping", "houthi", "yemen", "suez"],
                inferred_locations=[
                    GeoLocation(
                        latitude=15.5,
                        longitude=42.5,
                        name="Red Sea",
                        region_code="YE"
                    )
                ],
                market=MarketMetadata(
                    source="stub",
                    market_id=MarketId("stub-market-001"),
                    market_url="https://example.com/market/001",
                    total_volume_usd=500000.0,
                    current_liquidity_usd=75000.0,
                    num_traders=1200
                ),
                observed_at=datetime.utcnow()
            ),
            # Low-liquidity event (should be filtered)
            RawSignalEvent(
                event_id=EventId("test-low-liq-001"),
                title="Minor port delay in Southeast Asia",
                description="Will there be delays at a minor port?",
                probability=0.45,
                movement=None,
                keywords=["port", "delay", "asia"],
                inferred_locations=[],
                market=MarketMetadata(
                    source="stub",
                    market_id=MarketId("stub-market-002"),
                    total_volume_usd=500.0,
                    current_liquidity_usd=100.0,  # Below threshold
                ),
                observed_at=datetime.utcnow()
            ),
        ]
    
    @classmethod
    def create_red_sea_event(
        cls,
        probability: float = 0.75,
        liquidity: float = 50000.0
    ) -> RawSignalEvent:
        """Factory for Red Sea test events with configurable params."""
        return RawSignalEvent(
            event_id=EventId(f"test-rs-{datetime.utcnow().timestamp()}"),
            title="Red Sea shipping disruption",
            probability=probability,
            keywords=["red sea", "shipping", "houthi"],
            inferred_locations=[
                GeoLocation(latitude=15.5, longitude=42.5, name="Red Sea")
            ],
            market=MarketMetadata(
                source="stub",
                market_id=MarketId("test-market"),
                total_volume_usd=liquidity * 10,
                current_liquidity_usd=liquidity,
            )
        )
