"""
Multi-Source Signal Aggregator.

Integrates all signal sources (Polymarket, AIS, Weather, Freight) into
a unified signal stream with cross-source validation.

ENHANCED: Now uses FallbackStrategy for graceful degradation when sources fail.
"""

import logging
from typing import Iterator, AsyncIterator, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timezone

from omen.application.ports.signal_source import SignalSource
from omen.domain.models.raw_signal import RawSignalEvent
from omen.infrastructure.resilience.fallback_strategy import (
    FallbackCache,
    CachedData,
    FallbackResponse,
)

logger = logging.getLogger(__name__)


@dataclass
class SourceConfig:
    """Configuration for a signal source."""

    name: str
    enabled: bool = True
    priority: int = 1  # Higher = more important
    weight: float = 1.0  # Weight in confidence calculation
    cache_ttl_seconds: int = 3600  # 1 hour default cache TTL for fallback


@dataclass
class FetchResult:
    """Result of fetching from a source with fallback metadata."""
    
    events: list[RawSignalEvent]
    source_name: str
    is_fallback: bool = False
    fallback_reason: Optional[str] = None
    data_freshness: str = "live"
    data_age_seconds: Optional[float] = None


class MultiSourceAggregator:
    """
    Aggregates signals from multiple sources.

    Features:
    - Fetches from all enabled sources in parallel
    - Deduplicates similar signals
    - Enables cross-source validation
    - Provides unified signal stream
    - GRACEFUL DEGRADATION: Returns cached data when sources fail
    """

    def __init__(self, enable_fallback: bool = True):
        self._sources: dict[str, tuple[SignalSource, SourceConfig]] = {}
        self._enable_fallback = enable_fallback
        # Fallback caches per source for graceful degradation
        self._fallback_caches: dict[str, FallbackCache[list[RawSignalEvent]]] = {}

    def register_source(
        self,
        source: SignalSource,
        config: SourceConfig | None = None,
    ) -> None:
        """Register a signal source with automatic fallback cache."""
        name = source.source_name
        config = config or SourceConfig(name=name)
        self._sources[name] = (source, config)
        # Initialize fallback cache for this source
        self._fallback_caches[name] = FallbackCache[list[RawSignalEvent]](
            ttl_seconds=config.cache_ttl_seconds
        )
        logger.info(f"Registered source: {name} (enabled={config.enabled}, fallback_cache=enabled)")

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
        Fetch events from all enabled sources with graceful degradation.

        Args:
            limit_per_source: Max events per source
            sources: Optional list of source names to fetch from

        Returns:
            Combined list of events from all sources
            
        GRACEFUL DEGRADATION:
        - On source failure, returns cached (stale) data if available
        - Logs warning about data freshness
        - Never fails silently - always transparent about data quality
        """
        all_events: list[RawSignalEvent] = []
        fallback_sources: list[str] = []

        for name, (source, config) in self._sources.items():
            # Skip if source filtering is specified
            if sources and name not in sources:
                continue

            # Skip disabled sources
            if not config.enabled:
                continue

            cache_key = f"{name}_events_{limit_per_source}"
            
            try:
                logger.info(f"Fetching from source: {name}")
                events = list(source.fetch_events(limit=limit_per_source))
                logger.info(f"Source {name} returned {len(events)} events (LIVE)")
                
                # Cache successful result for fallback
                if self._enable_fallback and events:
                    self._fallback_caches[name].set(cache_key, events, name)
                
                all_events.extend(events)

            except Exception as e:
                logger.warning(f"Live fetch failed for {name}: {e}")
                
                # GRACEFUL DEGRADATION: Try to use cached data
                if self._enable_fallback and name in self._fallback_caches:
                    cached = self._fallback_caches[name].get_stale(cache_key)
                    if cached:
                        logger.warning(
                            f"Using STALE cache for {name} (age: {cached.age_seconds:.0f}s, "
                            f"freshness: {cached.freshness_level})"
                        )
                        all_events.extend(cached.data)
                        fallback_sources.append(f"{name}({cached.freshness_level})")
                    else:
                        logger.error(f"No cached data available for {name}, source unavailable")
                else:
                    logger.error(f"Fallback disabled or no cache for {name}: {e}")

        # Sort by timestamp (newest first)
        all_events.sort(
            key=lambda e: e.observed_at or datetime.min.replace(tzinfo=timezone.utc),
            reverse=True,
        )

        if fallback_sources:
            logger.warning(f"Used fallback data from: {fallback_sources}")
            
        logger.info(f"Total events from all sources: {len(all_events)} (fallback: {len(fallback_sources)} sources)")
        return all_events
    
    def fetch_all_with_metadata(
        self,
        limit_per_source: int = 50,
        sources: list[str] | None = None,
    ) -> tuple[list[RawSignalEvent], dict[str, FetchResult]]:
        """
        Fetch events with detailed metadata about each source.
        
        Returns:
            Tuple of (all_events, source_results) where source_results
            contains fallback status per source.
        """
        all_events: list[RawSignalEvent] = []
        source_results: dict[str, FetchResult] = {}

        for name, (source, config) in self._sources.items():
            if sources and name not in sources:
                continue
            if not config.enabled:
                continue

            cache_key = f"{name}_events_{limit_per_source}"
            
            try:
                events = list(source.fetch_events(limit=limit_per_source))
                
                if self._enable_fallback and events:
                    self._fallback_caches[name].set(cache_key, events, name)
                
                all_events.extend(events)
                source_results[name] = FetchResult(
                    events=events,
                    source_name=name,
                    is_fallback=False,
                    data_freshness="live",
                )

            except Exception as e:
                if self._enable_fallback and name in self._fallback_caches:
                    cached = self._fallback_caches[name].get_stale(cache_key)
                    if cached:
                        all_events.extend(cached.data)
                        source_results[name] = FetchResult(
                            events=cached.data,
                            source_name=name,
                            is_fallback=True,
                            fallback_reason=str(e),
                            data_freshness=cached.freshness_level,
                            data_age_seconds=cached.age_seconds,
                        )
                    else:
                        source_results[name] = FetchResult(
                            events=[],
                            source_name=name,
                            is_fallback=True,
                            fallback_reason=f"No cache: {e}",
                            data_freshness="unavailable",
                        )
                else:
                    source_results[name] = FetchResult(
                        events=[],
                        source_name=name,
                        is_fallback=True,
                        fallback_reason=str(e),
                        data_freshness="unavailable",
                    )

        all_events.sort(
            key=lambda e: e.observed_at or datetime.min.replace(tzinfo=timezone.utc),
            reverse=True,
        )

        return all_events, source_results

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
        """Get health status of all sources including fallback cache status."""
        health = {}

        for name, (source, config) in self._sources.items():
            cache_info = None
            if name in self._fallback_caches:
                cache = self._fallback_caches[name]
                cache_key = f"{name}_events_50"
                cached = cache.get_stale(cache_key)
                if cached:
                    cache_info = {
                        "has_cache": True,
                        "cache_age_seconds": int(cached.age_seconds),
                        "cache_freshness": cached.freshness_level,
                        "cache_expired": cached.is_expired,
                    }
                else:
                    cache_info = {"has_cache": False}
            
            try:
                # Try a minimal fetch to check health
                if config.enabled:
                    events = list(source.fetch_events(limit=1))
                    status = "healthy" if events else "no_data"
                else:
                    status = "disabled"
            except Exception as e:
                status = f"error: {str(e)[:50]}"
                # If we have cache, mark as degraded instead of error
                if cache_info and cache_info.get("has_cache"):
                    status = "degraded_with_fallback"

            health[name] = {
                "status": status,
                "enabled": config.enabled,
                "priority": config.priority,
                "fallback_cache": cache_info,
            }

        return health
    
    def get_fallback_stats(self) -> dict[str, Any]:
        """Get statistics about fallback caches."""
        stats = {
            "fallback_enabled": self._enable_fallback,
            "caches": {},
        }
        
        for name, cache in self._fallback_caches.items():
            stats["caches"][name] = cache.stats()
        
        return stats
    
    def clear_fallback_cache(self, source_name: Optional[str] = None) -> None:
        """Clear fallback cache for a specific source or all sources."""
        if source_name:
            if source_name in self._fallback_caches:
                self._fallback_caches[source_name].clear()
                logger.info(f"Cleared fallback cache for {source_name}")
        else:
            for name, cache in self._fallback_caches.items():
                cache.clear()
            logger.info("Cleared all fallback caches")


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
    """
    Register default sources based on environment configuration.
    
    IMPORTANT: No hardcoded mock scenarios! Sources use their config to determine
    whether to run in mock or real mode. The config is loaded from environment variables.
    """
    import os
    
    # Import sources
    # Try enhanced Polymarket source first (Gamma + CLOB for better accuracy)
    polymarket_registered = False
    try:
        from omen.adapters.inbound.polymarket.enhanced_source import EnhancedPolymarketSource
        from omen.adapters.inbound.polymarket.source import PolymarketSignalSource
        
        # Create enhanced source that combines Gamma + CLOB APIs
        enhanced = EnhancedPolymarketSource(logistics_only=False)
        
        # Wrap enhanced source to match SignalSource interface
        class EnhancedPolymarketWrapper:
            """Wrapper to make EnhancedPolymarketSource compatible with SignalSource interface."""
            
            source_name = "polymarket_enhanced"
            
            def __init__(self, enhanced_source: EnhancedPolymarketSource):
                self._enhanced = enhanced_source
            
            def fetch_events(self, limit: int = 50):
                """Fetch events using enhanced source."""
                return self._enhanced.fetch_events_enhanced(limit=limit)
        
        aggregator.register_source(
            EnhancedPolymarketWrapper(enhanced),
            SourceConfig(name="polymarket_enhanced", priority=3, weight=1.2),  # Higher priority + weight
        )
        logger.info("Registered Enhanced Polymarket source (Gamma + CLOB APIs)")
        polymarket_registered = True
    except Exception as e:
        logger.debug(f"Enhanced Polymarket source not available: {e}")
    
    # Fallback to standard Polymarket source
    if not polymarket_registered:
        try:
            from omen.adapters.inbound.polymarket.source import PolymarketSignalSource

            aggregator.register_source(
                PolymarketSignalSource(logistics_only=False),
                SourceConfig(name="polymarket", priority=2, weight=1.0),
            )
            logger.info("Registered Polymarket source (REAL API)")
        except ImportError as e:
            logger.warning(f"Could not load Polymarket source: {e}")

    try:
        from omen.adapters.inbound.ais.source import create_ais_source
        from omen.adapters.inbound.ais.config import AISConfig
        
        ais_config = AISConfig()  # Loads from OMEN_AIS_* env vars
        # Only pass scenario if explicitly using mock provider
        scenario = None if ais_config.provider != "mock" else os.getenv("OMEN_AIS_SCENARIO")
        source = create_ais_source(config=ais_config, scenario=scenario)
        aggregator.register_source(
            source,
            SourceConfig(name="ais", priority=1, weight=1.2),
        )
        logger.info(f"Registered AIS source (provider={ais_config.provider})")
    except ImportError as e:
        logger.warning(f"Could not load AIS source: {e}")

    try:
        from omen.adapters.inbound.weather.source import create_weather_source
        from omen.adapters.inbound.weather.config import WeatherConfig
        
        weather_config = WeatherConfig()  # Loads from OMEN_WEATHER_* env vars
        # Only pass scenario if explicitly using mock provider
        scenario = None if weather_config.provider != "mock" else os.getenv("OMEN_WEATHER_SCENARIO")
        source = create_weather_source(config=weather_config, scenario=scenario)
        aggregator.register_source(
            source,
            SourceConfig(name="weather", priority=1, weight=1.1),
        )
        logger.info(f"Registered Weather source (provider={weather_config.provider})")
    except ImportError as e:
        logger.warning(f"Could not load Weather source: {e}")

    try:
        from omen.adapters.inbound.freight.source import create_freight_source
        
        # Freight config loaded internally
        freight_provider = os.getenv("OMEN_FREIGHT_PROVIDER", "mock")
        scenario = None if freight_provider != "mock" else os.getenv("OMEN_FREIGHT_SCENARIO")
        source = create_freight_source(scenario=scenario)
        aggregator.register_source(
            source,
            SourceConfig(name="freight", priority=1, weight=1.0),
        )
        logger.info(f"Registered Freight source (provider={freight_provider})")
    except ImportError as e:
        logger.warning(f"Could not load Freight source: {e}")

    # Phase 2 sources: News and Commodity
    try:
        from omen.adapters.inbound.news.source import create_news_source
        
        news_api_key = os.getenv("NEWS_API_KEY")
        # Use real news if API key is available
        scenario = None if news_api_key else os.getenv("OMEN_NEWS_SCENARIO")
        source = create_news_source(scenario=scenario)
        aggregator.register_source(
            source,
            SourceConfig(name="news", priority=1, weight=0.8),
        )
        logger.info(f"Registered News source (has_api_key={bool(news_api_key)})")
    except ImportError as e:
        logger.warning(f"Could not load News source: {e}")

    try:
        from omen.adapters.inbound.commodity.source import create_commodity_source
        
        alpha_key = os.getenv("ALPHAVANTAGE_API_KEY")
        # Use real commodity if API key is available
        scenario = None if alpha_key else os.getenv("OMEN_COMMODITY_SCENARIO")
        source = create_commodity_source(scenario=scenario)
        aggregator.register_source(
            source,
            SourceConfig(name="commodity", priority=1, weight=0.7),
        )
        logger.info(f"Registered Commodity source (has_api_key={bool(alpha_key)})")
    except ImportError as e:
        logger.warning(f"Could not load Commodity source: {e}")

    # Stock source: Global + Vietnam markets
    try:
        from omen.adapters.inbound.stock.source import create_stock_source
        
        stock_provider = os.getenv("STOCK_PROVIDER", "both")
        source = create_stock_source(provider=stock_provider)
        aggregator.register_source(
            source,
            SourceConfig(name="stock", priority=2, weight=0.9),
        )
        logger.info(f"Registered Stock source (provider={stock_provider})")
    except ImportError as e:
        logger.warning(f"Could not load Stock source: {e}")
    
    # ✅ NEW: Vietnamese Logistics Partner Monitor
    # Monitors: GMD, HAH, VOS, VSC, PVT (Vietnamese logistics stocks)
    try:
        from omen.adapters.inbound.partner_risk.monitor import LogisticsSignalMonitor
        
        class LogisticsSourceWrapper:
            """Wrapper to make LogisticsSignalMonitor compatible with SignalSource."""
            
            source_name = "vietnamese_logistics"
            
            def __init__(self, monitor: LogisticsSignalMonitor):
                self._monitor = monitor
            
            def fetch_events(self, limit: int = 50):
                """Fetch Vietnamese logistics signals as raw events."""
                try:
                    signals_response = self._monitor.get_all_signals()
                    events = []
                    
                    for partner in signals_response.partners[:limit]:
                        # Convert partner signal to RawSignalEvent-like object
                        # This creates a signal from Vietnamese logistics data
                        if partner.signals.price_change_percent and abs(partner.signals.price_change_percent) > 3:
                            # Significant price movement - create event
                            from omen.domain.models.raw_signal import RawSignalEvent, MarketMetadata
                            from datetime import datetime, timezone
                            import uuid
                            
                            direction = "increased" if partner.signals.price_change_percent > 0 else "decreased"
                            event = RawSignalEvent(
                                event_id=str(uuid.uuid4()),
                                title=f"{partner.company_name} ({partner.symbol}) price {direction} {abs(partner.signals.price_change_percent):.1f}%",
                                description=partner.omen_suggestion or f"Vietnamese logistics stock {partner.symbol} showing significant price movement",
                                probability=0.5 + (partner.confidence.overall_confidence * 0.3),
                                market=MarketMetadata(
                                    market_id=f"vnstock_{partner.symbol}",
                                    source="vietnamese_logistics",
                                    current_liquidity_usd=partner.signals.volume * (partner.signals.price_current or 1000) / 24000 if partner.signals.volume else 10000,
                                ),
                                keywords=["vietnam", "logistics", partner.sector.lower(), partner.symbol.lower()],
                                source_name="vietnamese_logistics",
                                source_metrics={
                                    "symbol": partner.symbol,
                                    "sector": partner.sector,
                                    "price_change_pct": partner.signals.price_change_percent,
                                    "volume": partner.signals.volume,
                                    "pe_ratio": partner.signals.pe_ratio,
                                    "roe": partner.signals.roe,
                                    "confidence": partner.confidence.overall_confidence,
                                },
                            )
                            events.append(event)
                    
                    return iter(events)
                except Exception as e:
                    logger.warning(f"Failed to fetch Vietnamese logistics signals: {e}")
                    return iter([])
        
        logistics_monitor = LogisticsSignalMonitor(
            symbols=["GMD", "HAH", "VOS", "VSC", "PVT"],
            timeout_seconds=30.0,
        )
        aggregator.register_source(
            LogisticsSourceWrapper(logistics_monitor),
            SourceConfig(name="vietnamese_logistics", priority=2, weight=0.85),
        )
        logger.info("✅ Registered Vietnamese Logistics source (GMD, HAH, VOS, VSC, PVT)")
    except ImportError as e:
        logger.warning(f"Could not load Vietnamese Logistics source: {e}")
    except Exception as e:
        logger.warning(f"Vietnamese Logistics source registration failed: {e}")
    
    # Log summary of registered sources
    source_list = aggregator.list_sources()
    logger.info(f"✅ Multi-source aggregator initialized with {len(source_list)} sources")


def reset_aggregator() -> None:
    """Reset the global aggregator (for testing)."""
    global _aggregator
    _aggregator = None
