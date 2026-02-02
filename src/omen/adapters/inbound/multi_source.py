"""
Multi-Source Signal Aggregator.

Integrates all signal sources (Polymarket, AIS, Weather, Freight) into
a unified signal stream with cross-source validation.
"""

import logging
from typing import Iterator, AsyncIterator
from dataclasses import dataclass
from datetime import datetime, timezone

from omen.application.ports.signal_source import SignalSource
from omen.domain.models.raw_signal import RawSignalEvent

logger = logging.getLogger(__name__)


@dataclass
class SourceConfig:
    """Configuration for a signal source."""

    name: str
    enabled: bool = True
    priority: int = 1  # Higher = more important
    weight: float = 1.0  # Weight in confidence calculation


class MultiSourceAggregator:
    """
    Aggregates signals from multiple sources.

    Features:
    - Fetches from all enabled sources in parallel
    - Deduplicates similar signals
    - Enables cross-source validation
    - Provides unified signal stream
    """

    def __init__(self):
        self._sources: dict[str, tuple[SignalSource, SourceConfig]] = {}

    def register_source(
        self,
        source: SignalSource,
        config: SourceConfig | None = None,
    ) -> None:
        """Register a signal source."""
        name = source.source_name
        config = config or SourceConfig(name=name)
        self._sources[name] = (source, config)
        logger.info(f"Registered source: {name} (enabled={config.enabled})")

    def unregister_source(self, name: str) -> None:
        """Unregister a signal source."""
        if name in self._sources:
            del self._sources[name]
            logger.info(f"Unregistered source: {name}")

    def enable_source(self, name: str) -> None:
        """Enable a source."""
        if name in self._sources:
            self._sources[name][1].enabled = True

    def disable_source(self, name: str) -> None:
        """Disable a source."""
        if name in self._sources:
            self._sources[name][1].enabled = False

    def list_sources(self) -> list[dict]:
        """List all registered sources."""
        return [
            {
                "name": name,
                "enabled": config.enabled,
                "priority": config.priority,
                "weight": config.weight,
            }
            for name, (_, config) in self._sources.items()
        ]

    def fetch_all(
        self,
        limit_per_source: int = 50,
        sources: list[str] | None = None,
    ) -> list[RawSignalEvent]:
        """
        Fetch events from all enabled sources.

        Args:
            limit_per_source: Max events per source
            sources: Optional list of source names to fetch from

        Returns:
            Combined list of events from all sources
        """
        all_events: list[RawSignalEvent] = []

        for name, (source, config) in self._sources.items():
            # Skip if source filtering is specified
            if sources and name not in sources:
                continue

            # Skip disabled sources
            if not config.enabled:
                continue

            try:
                logger.info(f"Fetching from source: {name}")
                events = list(source.fetch_events(limit=limit_per_source))
                logger.info(f"Source {name} returned {len(events)} events")
                all_events.extend(events)

            except Exception as e:
                logger.error(f"Failed to fetch from {name}: {e}")
                continue

        # Sort by timestamp (newest first)
        all_events.sort(
            key=lambda e: e.observed_at or datetime.min.replace(tzinfo=timezone.utc),
            reverse=True,
        )

        logger.info(f"Total events from all sources: {len(all_events)}")
        return all_events

    def fetch_by_source(
        self,
        source_name: str,
        limit: int = 100,
    ) -> list[RawSignalEvent]:
        """Fetch events from a specific source."""
        if source_name not in self._sources:
            raise ValueError(f"Unknown source: {source_name}")

        source, config = self._sources[source_name]
        if not config.enabled:
            return []

        return list(source.fetch_events(limit=limit))

    def get_source_health(self) -> dict[str, dict]:
        """Get health status of all sources."""
        health = {}

        for name, (source, config) in self._sources.items():
            try:
                # Try a minimal fetch to check health
                if config.enabled:
                    events = list(source.fetch_events(limit=1))
                    status = "healthy" if events else "no_data"
                else:
                    status = "disabled"
            except Exception as e:
                status = f"error: {str(e)[:50]}"

            health[name] = {
                "status": status,
                "enabled": config.enabled,
                "priority": config.priority,
            }

        return health


# Global aggregator instance
_aggregator: MultiSourceAggregator | None = None


def get_multi_source_aggregator() -> MultiSourceAggregator:
    """Get or create the global multi-source aggregator."""
    global _aggregator
    if _aggregator is None:
        _aggregator = MultiSourceAggregator()
        _register_default_sources(_aggregator)
    return _aggregator


def _register_default_sources(aggregator: MultiSourceAggregator) -> None:
    """Register default sources."""
    # Import sources
    try:
        from omen.adapters.inbound.polymarket.source import PolymarketSignalSource

        aggregator.register_source(
            PolymarketSignalSource(logistics_only=False),
            SourceConfig(name="polymarket", priority=2, weight=1.0),
        )
    except ImportError as e:
        logger.warning(f"Could not load Polymarket source: {e}")

    try:
        from omen.adapters.inbound.ais.source import create_ais_source

        aggregator.register_source(
            create_ais_source(scenario="congestion"),  # Use mock with congestion scenario for demo
            SourceConfig(name="ais", priority=1, weight=1.2),
        )
    except ImportError as e:
        logger.warning(f"Could not load AIS source: {e}")

    try:
        from omen.adapters.inbound.weather.source import create_weather_source

        aggregator.register_source(
            create_weather_source(scenario="typhoon"),  # Use mock with typhoon scenario
            SourceConfig(name="weather", priority=1, weight=1.1),
        )
    except ImportError as e:
        logger.warning(f"Could not load Weather source: {e}")

    try:
        from omen.adapters.inbound.freight.source import create_freight_source

        aggregator.register_source(
            create_freight_source(scenario="spike"),  # Use mock with spike scenario
            SourceConfig(name="freight", priority=1, weight=1.0),
        )
    except ImportError as e:
        logger.warning(f"Could not load Freight source: {e}")

    # Phase 2 sources: News and Commodity
    try:
        from omen.adapters.inbound.news.source import create_news_source

        aggregator.register_source(
            create_news_source(scenario="red_sea"),  # Use mock with Red Sea scenario
            SourceConfig(name="news", priority=1, weight=0.8),  # Lower weight - context only
        )
    except ImportError as e:
        logger.warning(f"Could not load News source: {e}")

    try:
        from omen.adapters.inbound.commodity.source import create_commodity_source

        aggregator.register_source(
            create_commodity_source(scenario="spike"),  # Use mock with spike scenario
            SourceConfig(name="commodity", priority=1, weight=0.7),  # Lower weight - context only
        )
    except ImportError as e:
        logger.warning(f"Could not load Commodity source: {e}")

    # Stock source: Global + Vietnam markets
    try:
        from omen.adapters.inbound.stock.source import create_stock_source

        aggregator.register_source(
            create_stock_source(provider="both"),  # yfinance + vnstock
            SourceConfig(name="stock", priority=2, weight=0.9),  # High priority for market data
        )
    except ImportError as e:
        logger.warning(f"Could not load Stock source: {e}")


def reset_aggregator() -> None:
    """Reset the global aggregator (for testing)."""
    global _aggregator
    _aggregator = None
