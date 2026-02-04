"""
Background Signal Generator

Periodically fetches data from all available sources and generates LIVE signals.
This ensures the system always has fresh, real data when in LIVE mode.
"""

import asyncio
import hashlib
import logging
import os
import random
import time
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Callable

logger = logging.getLogger(__name__)


class BackgroundSignalGenerator:
    """
    Background service that periodically generates LIVE signals from all data sources.
    
    This service:
    1. Polls data sources at configurable intervals
    2. Generates signals with OMEN-LIVE prefix
    3. Stores signals in the repository
    4. Tracks source health and metrics
    """
    
    def __init__(
        self,
        interval_seconds: int = 120,
        initial_delay_seconds: int = 5,
    ):
        self.interval_seconds = interval_seconds
        self.initial_delay_seconds = initial_delay_seconds
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._last_run: Optional[datetime] = None
        self._run_count = 0
        self._signals_generated = 0
        self._source_stats: Dict[str, Dict[str, Any]] = {}
        
    @property
    def is_running(self) -> bool:
        return self._running
    
    @property
    def stats(self) -> Dict[str, Any]:
        return {
            "running": self._running,
            "last_run": self._last_run.isoformat() if self._last_run else None,
            "run_count": self._run_count,
            "signals_generated": self._signals_generated,
            "source_stats": self._source_stats,
            "interval_seconds": self.interval_seconds,
        }
    
    def start(self) -> None:
        """Start the background generator."""
        if self._running:
            logger.warning("Background signal generator already running")
            return
        
        self._running = True
        
        # Get the current event loop and create task
        try:
            loop = asyncio.get_running_loop()
            self._task = loop.create_task(self._run_loop())
        except RuntimeError:
            # No running loop, schedule for later
            self._task = asyncio.ensure_future(self._run_loop())
        
        logger.info(
            f"Background signal generator started (interval: {self.interval_seconds}s, "
            f"initial delay: {self.initial_delay_seconds}s)"
        )
    
    def stop(self) -> None:
        """Stop the background generator."""
        self._running = False
        if self._task:
            self._task.cancel()
            self._task = None
        logger.info("Background signal generator stopped")
    
    async def _run_loop(self) -> None:
        """Main generation loop."""
        # Wait for initial delay to let the app fully start
        await asyncio.sleep(self.initial_delay_seconds)
        
        # Generate initial batch
        try:
            await self._generate_cycle()
        except Exception as e:
            logger.error(f"Initial signal generation failed: {e}")
        
        # Continue periodic generation
        while self._running:
            try:
                await asyncio.sleep(self.interval_seconds)
                if self._running:
                    await self._generate_cycle()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Signal generation cycle failed: {e}")
                # Continue anyway, don't let errors stop the loop
    
    async def _generate_cycle(self) -> Dict[str, Any]:
        """Run one cycle of signal generation."""
        from omen.api.dependencies import get_repository
        from omen.infrastructure.activity.activity_logger import get_activity_logger
        
        start_time = time.time()
        self._last_run = datetime.now(timezone.utc)
        self._run_count += 1
        
        repository = get_repository()
        activity = get_activity_logger()
        
        results = {
            "cycle": self._run_count,
            "started_at": self._last_run.isoformat(),
            "sources": {},
            "signals_created": 0,
        }
        
        # Fetch from all sources in parallel
        source_results = await asyncio.gather(
            self._generate_from_polymarket(repository),
            self._generate_from_weather(repository),
            self._generate_from_news(repository),
            self._generate_from_stock(repository),
            return_exceptions=True,
        )
        
        source_names = ["polymarket", "weather", "news", "stock"]
        total_created = 0
        
        for i, result in enumerate(source_results):
            source_name = source_names[i]
            if isinstance(result, Exception):
                results["sources"][source_name] = {
                    "status": "error",
                    "error": str(result),
                    "signals_created": 0,
                }
                self._source_stats[source_name] = {
                    "status": "error",
                    "last_error": str(result),
                    "last_check": datetime.now(timezone.utc).isoformat(),
                }
                logger.warning(f"Source {source_name} failed: {result}")
            else:
                count = result if isinstance(result, int) else 0
                total_created += count
                results["sources"][source_name] = {
                    "status": "ok",
                    "signals_created": count,
                }
                self._source_stats[source_name] = {
                    "status": "connected",
                    "signals_created": count,
                    "last_check": datetime.now(timezone.utc).isoformat(),
                }
        
        self._signals_generated += total_created
        results["signals_created"] = total_created
        results["duration_ms"] = (time.time() - start_time) * 1000
        
        if total_created > 0:
            activity.log_system_event(
                f"Background generation: {total_created} LIVE signals from "
                f"{sum(1 for s in results['sources'].values() if s['status'] == 'ok')} sources"
            )
            logger.info(f"Generated {total_created} LIVE signals in cycle {self._run_count}")
        
        return results
    
    def _generate_live_signal_id(self) -> str:
        """Generate a unique LIVE signal ID."""
        timestamp = datetime.now(timezone.utc).timestamp()
        random_part = random.randint(1000, 9999)
        hash_input = f"{timestamp}-{random_part}"
        hash_hex = hashlib.md5(hash_input.encode()).hexdigest()[:8].upper()
        return f"OMEN-LIVE{hash_hex}"
    
    async def _generate_from_polymarket(self, repository) -> int:
        """Generate signals from Polymarket."""
        try:
            from omen.adapters.inbound.polymarket.source import PolymarketSignalSource
            from omen.api.dependencies import get_signal_only_pipeline
            from omen.infrastructure.activity.activity_logger import get_activity_logger
            
            activity = get_activity_logger()
            source = PolymarketSignalSource(logistics_only=False)
            
            start = time.time()
            raw_events = list(source.fetch_events(limit=50))
            fetch_time = (time.time() - start) * 1000
            
            if not raw_events:
                return 0
            
            activity.log_source_fetch(
                source_name="Polymarket",
                events_count=len(raw_events),
                latency_ms=fetch_time,
                success=True,
            )
            
            # Filter by liquidity
            filtered = [e for e in raw_events if e.market.current_liquidity_usd >= 1000][:30]
            
            pipeline = get_signal_only_pipeline()
            results = pipeline.process_batch(filtered)
            
            signals_created = 0
            for r in results:
                if r.success and r.signal is not None:
                    # Override the signal_id to use LIVE prefix
                    # We need to create a new signal with the LIVE ID
                    signal = r.signal
                    # Create signal with LIVE ID by modifying the signal dict
                    signal_dict = signal.model_dump()
                    signal_dict["signal_id"] = self._generate_live_signal_id()
                    
                    from omen.domain.models.omen_signal import OmenSignal
                    live_signal = OmenSignal.model_validate(signal_dict)
                    
                    repository.save(live_signal)
                    signals_created += 1
                    
                    activity.log_signal_generated(
                        signal_id=live_signal.signal_id,
                        title=live_signal.title,
                        confidence_label=live_signal.confidence_level.value,
                        confidence_level=str(live_signal.confidence_score),
                    )
            
            return signals_created
            
        except Exception as e:
            logger.warning(f"Polymarket generation failed: {e}")
            raise
    
    async def _generate_from_weather(self, repository) -> int:
        """Generate signals from weather data."""
        try:
            from omen.adapters.inbound.weather.openmeteo_adapter import get_openmeteo_adapter
            from omen.domain.models.omen_signal import (
                OmenSignal, ConfidenceLevel, SignalCategory,
                EvidenceItem, GeographicContext, TemporalContext,
            )
            from omen.infrastructure.activity.activity_logger import get_activity_logger
            
            activity = get_activity_logger()
            adapter = get_openmeteo_adapter()
            signals_created = 0
            now = datetime.now(timezone.utc)
            
            # Check weather for major shipping ports
            ports = ["singapore", "shanghai", "ho_chi_minh", "rotterdam"]
            
            for port_key in ports:
                try:
                    weather = await adapter.get_port_weather(port_key)
                    
                    # Only create signal for significant weather
                    if weather.is_severe or weather.wind_speed_kmh > 40:
                        severity = "Severe" if weather.is_severe else "High Winds"
                        confidence = 0.85 if weather.is_severe else 0.70
                        
                        signal = OmenSignal(
                            signal_id=self._generate_live_signal_id(),
                            source_event_id=f"weather-{port_key}-{now.timestamp()}",
                            title=f"{severity} Weather Alert: {weather.location}",
                            description=f"{weather.weather_description}. Wind: {weather.wind_speed_kmh:.0f} km/h, Temp: {weather.temperature_c:.1f}°C",
                            probability=0.80 if weather.is_severe else 0.65,
                            probability_source="openmeteo",
                            confidence_score=confidence,
                            confidence_level=ConfidenceLevel.from_score(confidence),
                            category=SignalCategory.WEATHER,
                            tags=[port_key, "weather", "shipping"],
                            geographic=GeographicContext(
                                regions=[port_key],
                                chokepoints=[],
                            ),
                            temporal=TemporalContext(
                                event_horizon=now.strftime("%Y-%m-%d"),
                                resolution_date=now + timedelta(hours=24),
                            ),
                            evidence=[
                                EvidenceItem(
                                    source="Open-Meteo",
                                    source_type="api",
                                    url="https://open-meteo.com",
                                    observed_at=now,
                                )
                            ],
                            trace_id=f"weather-{now.strftime('%Y%m%d%H%M%S')}",
                            ruleset_version="1.0.0",
                            source_url="https://open-meteo.com",
                            observed_at=now,
                            generated_at=now,
                        )
                        
                        repository.save(signal)
                        signals_created += 1
                        
                        activity.log_signal_generated(
                            signal_id=signal.signal_id,
                            title=signal.title,
                            confidence_label=signal.confidence_level.value,
                            confidence_level=str(signal.confidence_score),
                        )
                        
                except Exception as e:
                    logger.debug(f"Weather check for {port_key} failed: {e}")
            
            return signals_created
            
        except ImportError as e:
            logger.debug(f"Weather adapter not available: {e}")
            return 0
        except Exception as e:
            logger.warning(f"Weather generation failed: {e}")
            raise
    
    async def _generate_from_news(self, repository) -> int:
        """Generate signals from news data."""
        try:
            from omen.adapters.inbound.news.newsdata_adapter import get_newsdata_adapter
            from omen.domain.models.omen_signal import (
                OmenSignal, ConfidenceLevel, SignalCategory,
                EvidenceItem, GeographicContext, TemporalContext,
            )
            from omen.infrastructure.activity.activity_logger import get_activity_logger
            
            activity = get_activity_logger()
            adapter = get_newsdata_adapter()
            signals_created = 0
            now = datetime.now(timezone.utc)
            
            articles = await adapter.get_logistics_news(size=10)
            
            for article in articles[:5]:
                try:
                    # Determine category
                    title_lower = article.title.lower()
                    if any(kw in title_lower for kw in ["tariff", "sanction", "regulation", "policy", "law"]):
                        category = SignalCategory.REGULATORY
                    elif any(kw in title_lower for kw in ["war", "conflict", "military", "attack", "election"]):
                        category = SignalCategory.GEOPOLITICAL
                    elif any(kw in title_lower for kw in ["price", "cost", "market", "stock", "rate"]):
                        category = SignalCategory.ECONOMIC
                    elif any(kw in title_lower for kw in ["port", "ship", "freight", "container"]):
                        category = SignalCategory.INFRASTRUCTURE
                    else:
                        category = SignalCategory.OTHER
                    
                    # Calculate confidence
                    confidence = 0.65
                    if article.sentiment == "negative":
                        confidence = 0.75
                    elif article.sentiment == "positive":
                        confidence = 0.70
                    
                    signal = OmenSignal(
                        signal_id=self._generate_live_signal_id(),
                        source_event_id=f"news-{now.timestamp()}-{random.randint(100, 999)}",
                        title=article.title[:200],
                        description=(article.description or "")[:500],
                        probability=0.5 + (article.sentiment_score * 0.2),
                        probability_source="newsdata",
                        confidence_score=confidence,
                        confidence_level=ConfidenceLevel.from_score(confidence),
                        category=category,
                        tags=["news", category.value.lower()],
                        geographic=GeographicContext(
                            regions=article.country if article.country else [],
                            chokepoints=[],
                        ),
                        temporal=TemporalContext(
                            event_horizon=now.strftime("%Y-%m-%d"),
                            resolution_date=now + timedelta(hours=48),
                        ),
                        evidence=[
                            EvidenceItem(
                                source=article.source_name or "NewsData",
                                source_type="news",
                                url=article.link,
                                observed_at=now,
                            )
                        ],
                        trace_id=f"news-{now.strftime('%Y%m%d%H%M%S')}",
                        ruleset_version="1.0.0",
                        source_url=article.link,
                        observed_at=now,
                        generated_at=now,
                    )
                    
                    repository.save(signal)
                    signals_created += 1
                    
                    activity.log_signal_generated(
                        signal_id=signal.signal_id,
                        title=signal.title,
                        confidence_label=signal.confidence_level.value,
                        confidence_level=str(signal.confidence_score),
                    )
                    
                except Exception as e:
                    logger.debug(f"Failed to process news article: {e}")
            
            return signals_created
            
        except ImportError as e:
            logger.debug(f"News adapter not available: {e}")
            return 0
        except Exception as e:
            logger.warning(f"News generation failed: {e}")
            raise
    
    async def _generate_from_stock(self, repository) -> int:
        """Generate signals from stock/market data."""
        try:
            import httpx
            from omen.domain.models.omen_signal import (
                OmenSignal, ConfidenceLevel, SignalCategory,
                EvidenceItem, GeographicContext, TemporalContext,
            )
            from omen.infrastructure.activity.activity_logger import get_activity_logger
            
            activity = get_activity_logger()
            signals_created = 0
            now = datetime.now(timezone.utc)
            
            # Track key market indices and commodities
            symbols = {
                "^GSPC": ("S&P 500", SignalCategory.ECONOMIC),
                "^VIX": ("VIX Volatility Index", SignalCategory.ECONOMIC),
                "CL=F": ("Crude Oil Futures", SignalCategory.ECONOMIC),
            }
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                for symbol, (name, category) in symbols.items():
                    try:
                        response = await client.get(
                            f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}",
                            params={"interval": "1d", "range": "5d"},
                        )
                        
                        if response.status_code != 200:
                            continue
                        
                        data = response.json()
                        result = data.get("chart", {}).get("result", [{}])[0]
                        
                        # Get price data
                        indicators = result.get("indicators", {}).get("quote", [{}])[0]
                        closes = indicators.get("close", [])
                        
                        if len(closes) < 2:
                            continue
                        
                        # Filter out None values
                        closes = [c for c in closes if c is not None]
                        if len(closes) < 2:
                            continue
                        
                        current = closes[-1]
                        previous = closes[-2]
                        change_pct = ((current - previous) / previous) * 100
                        
                        # Only signal significant moves (>2%)
                        if abs(change_pct) < 2:
                            continue
                        
                        direction = "surged" if change_pct > 0 else "dropped"
                        confidence = 0.80 if abs(change_pct) > 3 else 0.70
                        
                        signal = OmenSignal(
                            signal_id=self._generate_live_signal_id(),
                            source_event_id=f"stock-{symbol}-{now.timestamp()}",
                            title=f"{name} {direction} {abs(change_pct):.1f}%",
                            description=f"{name} ({symbol}) moved significantly. Current: ${current:.2f}",
                            probability=0.85 if abs(change_pct) > 3 else 0.70,
                            probability_source="yahoo_finance",
                            confidence_score=confidence,
                            confidence_level=ConfidenceLevel.from_score(confidence),
                            category=category,
                            tags=["market", symbol.lower()],
                            geographic=GeographicContext(
                                regions=["global"],
                                chokepoints=[],
                            ),
                            temporal=TemporalContext(
                                event_horizon=now.strftime("%Y-%m-%d"),
                                resolution_date=now + timedelta(hours=24),
                            ),
                            evidence=[
                                EvidenceItem(
                                    source="Yahoo Finance",
                                    source_type="market",
                                    url=f"https://finance.yahoo.com/quote/{symbol}",
                                    observed_at=now,
                                )
                            ],
                            trace_id=f"stock-{now.strftime('%Y%m%d%H%M%S')}",
                            ruleset_version="1.0.0",
                            source_url=f"https://finance.yahoo.com/quote/{symbol}",
                            observed_at=now,
                            generated_at=now,
                        )
                        
                        repository.save(signal)
                        signals_created += 1
                        
                        activity.log_signal_generated(
                            signal_id=signal.signal_id,
                            title=signal.title,
                            confidence_label=signal.confidence_level.value,
                            confidence_level=str(signal.confidence_score),
                        )
                        
                    except Exception as e:
                        logger.debug(f"Stock check for {symbol} failed: {e}")
            
            return signals_created
            
        except Exception as e:
            logger.warning(f"Stock generation failed: {e}")
            raise
    
    async def generate_now(self) -> Dict[str, Any]:
        """Manually trigger a generation cycle."""
        return await self._generate_cycle()


# Global instance
_generator_instance: Optional[BackgroundSignalGenerator] = None


def get_background_generator() -> BackgroundSignalGenerator:
    """Get or create the global background generator instance."""
    global _generator_instance
    if _generator_instance is None:
        interval = int(os.getenv("OMEN_SIGNAL_POLL_INTERVAL", "120"))
        _generator_instance = BackgroundSignalGenerator(
            interval_seconds=interval,
            initial_delay_seconds=5,
        )
    return _generator_instance


def start_background_generator() -> None:
    """Start the background signal generator."""
    generator = get_background_generator()
    generator.start()


def stop_background_generator() -> None:
    """Stop the background signal generator."""
    generator = get_background_generator()
    generator.stop()
