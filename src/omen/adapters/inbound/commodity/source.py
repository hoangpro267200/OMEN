"""
Commodity Signal Source.

Implements SignalSource interface for commodity price data.
Provides macro/leading indicators through spike detection.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Iterator, AsyncIterator

from omen.application.ports.signal_source import SignalSource
from omen.domain.models.raw_signal import RawSignalEvent

from .config import CommodityConfig
from .client import CommodityClient, MockCommodityClient, create_commodity_client
from .spike_detector import SpikeDetector
from .mapper import CommodityMapper

logger = logging.getLogger(__name__)


class CommoditySignalSource(SignalSource):
    """
    Commodity price source for OMEN.
    
    Features:
    - Fetches prices for configured commodities
    - Detects price spikes deterministically
    - Maps spikes to RawSignalEvent
    - Supports replay via asof_ts
    
    Note: Commodity signals are context/indicators, not primary risk signals.
    They should be used to confirm or weight other signals, not as standalone.
    """
    
    def __init__(
        self,
        client: CommodityClient | MockCommodityClient | None = None,
        spike_detector: SpikeDetector | None = None,
        mapper: CommodityMapper | None = None,
        config: CommodityConfig | None = None,
    ):
        self._config = config or CommodityConfig()
        self._client = client or create_commodity_client(self._config)
        self._spike_detector = spike_detector or SpikeDetector(self._config)
        self._mapper = mapper or CommodityMapper(self._config)
        self._watchlist = self._config.get_watchlist()
        
        # Cache for replay
        self._cached_events: list[RawSignalEvent] | None = None
        self._cache_timestamp: datetime | None = None
    
    @property
    def source_name(self) -> str:
        return "commodity"
    
    def fetch_events(
        self,
        limit: int = 100,
        asof_ts: datetime | None = None,
    ) -> Iterator[RawSignalEvent]:
        """
        Fetch commodity spike events.
        
        Args:
            limit: Maximum events to return
            asof_ts: Reference time for replay mode.
                     If provided and cache exists, uses cached data.
        
        Yields:
            RawSignalEvent for detected spikes
        """
        # Replay mode: use cached data
        if asof_ts is not None and self._cached_events is not None:
            logger.info(
                f"Commodity source: replay mode with {len(self._cached_events)} cached events"
            )
            for event in self._cached_events[:limit]:
                yield event
            return
        
        # Live mode: fetch from API
        events: list[RawSignalEvent] = []
        now = datetime.now(timezone.utc)
        
        logger.info(f"Checking {len(self._watchlist)} commodities for spikes")
        
        for item in self._watchlist:
            if len(events) >= limit:
                break
            
            try:
                logger.debug(f"Fetching {item.symbol}")
                
                # Get price series
                series = self._client.get_daily_prices(
                    item.alphavantage_symbol,
                    outputsize="compact",
                )
                
                # Detect spike
                spike = self._spike_detector.detect(series, item)
                
                if spike and spike.is_spike:
                    logger.info(
                        f"Spike detected: {spike.symbol} {spike.direction} "
                        f"{spike.pct_change:+.1f}% [{spike.severity}]"
                    )
                    
                    # Map to event
                    event = self._mapper.map_spike(spike, asof_ts=now)
                    
                    if event:
                        events.append(event)
                else:
                    logger.debug(f"No spike for {item.symbol}")
                    
            except Exception as e:
                logger.error(f"Failed to process {item.symbol}: {e}")
                continue
        
        logger.info(f"Commodity source found {len(events)} spike events")
        
        # Cache for potential replay
        self._cached_events = events
        self._cache_timestamp = now
        
        for event in events:
            yield event
    
    async def fetch_events_async(
        self,
        limit: int = 100,
    ) -> AsyncIterator[RawSignalEvent]:
        """Async version of fetch_events."""
        for event in self.fetch_events(limit):
            yield event
    
    def fetch_by_id(self, market_id: str) -> RawSignalEvent | None:
        """
        Fetch specific commodity event by market_id.
        
        market_id format: "{SYMBOL}-{YYYYMMDD}"
        """
        if self._cached_events:
            for event in self._cached_events:
                if event.market.market_id == market_id:
                    return event
        
        # Try to fetch fresh
        parts = market_id.split("-")
        if len(parts) < 2:
            return None
        
        symbol = parts[0].upper()
        
        for item in self._watchlist:
            if item.symbol == symbol:
                try:
                    series = self._client.get_daily_prices(
                        item.alphavantage_symbol,
                        outputsize="compact",
                    )
                    spike = self._spike_detector.detect(series, item)
                    
                    if spike and spike.is_spike:
                        return self._mapper.map_spike(spike)
                        
                except Exception as e:
                    logger.error(f"Failed to fetch {symbol}: {e}")
                break
        
        return None
    
    def set_cached_events(self, events: list[RawSignalEvent]) -> None:
        """Set cached events for replay mode."""
        self._cached_events = events
        self._cache_timestamp = datetime.now(timezone.utc)
    
    def clear_cache(self) -> None:
        """Clear cached events."""
        self._cached_events = None
        self._cache_timestamp = None


class MockCommoditySignalSource(CommoditySignalSource):
    """
    Mock commodity source for testing.
    """
    
    def __init__(
        self,
        scenario: str = "spike",
        config: CommodityConfig | None = None,
    ):
        """
        Initialize mock source.
        
        Args:
            scenario: Simulation scenario
                - "spike": Recent price spikes
                - "crash": Recent price crashes
                - "normal": No significant moves
            config: Optional config override
        """
        config = config or CommodityConfig()
        client = MockCommodityClient(config, scenario=scenario)
        super().__init__(client=client, config=config)
        self._scenario = scenario
    
    @property
    def scenario(self) -> str:
        return self._scenario


def create_commodity_source(
    config: CommodityConfig | None = None,
    scenario: str | None = None,
) -> CommoditySignalSource:
    """
    Factory function to create commodity signal source.
    
    Args:
        config: Commodity configuration
        scenario: If provided, creates mock source with scenario
    
    Returns:
        CommoditySignalSource instance
    """
    config = config or CommodityConfig()
    
    if scenario or config.provider == "mock":
        return MockCommoditySignalSource(
            scenario=scenario or "spike",
            config=config,
        )
    
    return CommoditySignalSource(config=config)
