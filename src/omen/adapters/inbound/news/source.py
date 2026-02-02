"""
News Signal Source.

Implements SignalSource interface for news data.
Provides early detection and context confirmation through news analysis.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from typing import Iterator, AsyncIterator

from omen.application.ports.signal_source import SignalSource
from omen.domain.models.raw_signal import RawSignalEvent

from .config import NewsConfig
from .client import NewsClient, MockNewsClient, create_news_client
from .quality_gate import NewsQualityGate
from .mapper import NewsMapper

logger = logging.getLogger(__name__)


# Default search queries for logistics-relevant news
DEFAULT_QUERIES = [
    "red sea shipping",
    "suez canal",
    "panama canal",
    "port strike",
    "shipping disruption",
    "freight rates",
    "supply chain disruption",
]


class NewsSignalSource(SignalSource):
    """
    News data source for OMEN.
    
    Features:
    - Fetches news from NewsAPI or RSS
    - Quality gates (credibility, recency, dedup)
    - Maps to RawSignalEvent
    - Supports deterministic replay via asof_ts
    
    Usage modes:
    - Live: fetch_events() - uses current time
    - Replay: fetch_events(asof_ts=...) - no network, cached data
    """
    
    def __init__(
        self,
        client: NewsClient | MockNewsClient | None = None,
        quality_gate: NewsQualityGate | None = None,
        mapper: NewsMapper | None = None,
        config: NewsConfig | None = None,
        queries: list[str] | None = None,
    ):
        self._config = config or NewsConfig()
        self._client = client or create_news_client(self._config)
        self._quality_gate = quality_gate or NewsQualityGate(self._config)
        self._mapper = mapper or NewsMapper(self._config)
        self._queries = queries or DEFAULT_QUERIES
        
        # Cache for replay mode
        self._cached_events: list[RawSignalEvent] | None = None
        self._cache_timestamp: datetime | None = None
    
    @property
    def source_name(self) -> str:
        return "news"
    
    def fetch_events(
        self,
        limit: int = 100,
        asof_ts: datetime | None = None,
    ) -> Iterator[RawSignalEvent]:
        """
        Fetch news events.
        
        Args:
            limit: Maximum events to return
            asof_ts: Reference time for replay mode.
                     If provided, uses cached data (no network).
                     If None, fetches live data.
        
        Yields:
            RawSignalEvent from news articles
        """
        # Replay mode: use cached data
        if asof_ts is not None and self._cached_events is not None:
            logger.info(f"News source: replay mode with {len(self._cached_events)} cached events")
            for event in self._cached_events[:limit]:
                yield event
            return
        
        # Live mode: fetch from API
        events: list[RawSignalEvent] = []
        
        # Reset dedupe cache for fresh fetch
        self._quality_gate.reset_dedupe_cache()
        
        # Calculate date range (last N hours based on config)
        now = datetime.now(timezone.utc)
        from_date = now - timedelta(hours=self._config.max_age_hours)
        
        for query in self._queries:
            if len(events) >= limit:
                break
            
            try:
                logger.info(f"Searching news: '{query}'")
                
                for article in self._client.search(
                    query=query,
                    from_date=from_date,
                    to_date=now,
                    page_size=min(50, limit - len(events)),
                ):
                    # Quality gate
                    quality = self._quality_gate.evaluate(article, asof_ts=now)
                    
                    if not quality.passed_gate:
                        logger.debug(
                            f"Article rejected: {quality.rejection_reason} - {article.title[:50]}"
                        )
                        continue
                    
                    # Map to RawSignalEvent
                    event = self._mapper.map_article(article, quality, asof_ts=now)
                    
                    if event:
                        events.append(event)
                        logger.info(
                            f"News event: [{event.probability:.0%}] {event.title[:60]}..."
                        )
                    
                    if len(events) >= limit:
                        break
                        
            except Exception as e:
                logger.error(f"Failed to search news for '{query}': {e}")
                continue
        
        logger.info(f"News source found {len(events)} events")
        
        # Cache for potential replay
        self._cached_events = events
        self._cache_timestamp = now
        
        for event in events:
            yield event
    
    async def fetch_events_async(
        self,
        limit: int = 100,
    ) -> AsyncIterator[RawSignalEvent]:
        """
        Async version of fetch_events.
        
        Currently wraps sync method. Can be optimized with async client.
        """
        for event in self.fetch_events(limit):
            yield event
    
    def fetch_by_id(self, market_id: str) -> RawSignalEvent | None:
        """
        Fetch specific news event by market_id (URL hash).
        
        Searches cached events first, then returns None if not found.
        (News articles are not individually fetchable by ID)
        """
        if self._cached_events:
            for event in self._cached_events:
                if event.market.market_id == market_id:
                    return event
        return None
    
    def search(self, query: str, limit: int = 20) -> Iterator[RawSignalEvent]:
        """
        Search for specific news topics.
        
        Uses custom query instead of default queries.
        """
        self._quality_gate.reset_dedupe_cache()
        now = datetime.now(timezone.utc)
        from_date = now - timedelta(hours=self._config.max_age_hours)
        
        count = 0
        
        try:
            for article in self._client.search(
                query=query,
                from_date=from_date,
                to_date=now,
                page_size=limit,
            ):
                quality = self._quality_gate.evaluate(article, asof_ts=now)
                
                if not quality.passed_gate:
                    continue
                
                event = self._mapper.map_article(article, quality, asof_ts=now)
                
                if event:
                    yield event
                    count += 1
                    
                if count >= limit:
                    break
                    
        except Exception as e:
            logger.error(f"News search failed: {e}")
    
    def set_cached_events(self, events: list[RawSignalEvent]) -> None:
        """Set cached events for replay mode."""
        self._cached_events = events
        self._cache_timestamp = datetime.now(timezone.utc)
    
    def clear_cache(self) -> None:
        """Clear cached events."""
        self._cached_events = None
        self._cache_timestamp = None


class MockNewsSignalSource(NewsSignalSource):
    """
    Mock news source for testing with configurable scenarios.
    """
    
    def __init__(
        self,
        scenario: str = "red_sea",
        config: NewsConfig | None = None,
    ):
        """
        Initialize mock source.
        
        Args:
            scenario: Simulation scenario
                - "red_sea": Red Sea shipping attacks
                - "port_strike": Port worker strikes
                - "panama": Panama Canal drought
            config: Optional config override
        """
        config = config or NewsConfig()
        client = MockNewsClient(config, scenario=scenario)
        super().__init__(client=client, config=config)
        self._scenario = scenario
    
    @property
    def scenario(self) -> str:
        return self._scenario


def create_news_source(
    config: NewsConfig | None = None,
    scenario: str | None = None,
    queries: list[str] | None = None,
) -> NewsSignalSource:
    """
    Factory function to create news signal source.
    
    Args:
        config: News configuration
        scenario: If provided, creates mock source with scenario
        queries: Custom search queries (optional)
    
    Returns:
        NewsSignalSource instance
    """
    config = config or NewsConfig()
    
    if scenario or config.provider == "mock":
        return MockNewsSignalSource(
            scenario=scenario or "red_sea",
            config=config,
        )
    
    return NewsSignalSource(config=config, queries=queries)
