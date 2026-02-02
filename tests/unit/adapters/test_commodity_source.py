"""
Comprehensive tests for Commodity Source adapter.

Tests cover:
1. SpikeDetector: baseline, pct_change, zscore, severity
2. CommodityMapper: event creation, determinism
3. CommoditySignalSource: live/replay modes
4. Determinism & JSON safety: bounded zscore, no NaN/Inf
"""

import pytest
import json
import math
from datetime import datetime, timezone, timedelta

from omen.adapters.inbound.commodity.config import CommodityConfig, CommodityWatchlistItem
from omen.adapters.inbound.commodity.schemas import PriceTimeSeries, CommoditySpike
from omen.adapters.inbound.commodity.spike_detector import SpikeDetector, detect_spike_from_prices
from omen.adapters.inbound.commodity.mapper import CommodityMapper
from omen.adapters.inbound.commodity.source import MockCommoditySignalSource, create_commodity_source


# ═══════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def config() -> CommodityConfig:
    """Create test commodity config."""
    return CommodityConfig()


@pytest.fixture
def spike_detector(config: CommodityConfig) -> SpikeDetector:
    """Create spike detector instance."""
    return SpikeDetector(config)


@pytest.fixture
def mapper(config: CommodityConfig) -> CommodityMapper:
    """Create mapper instance."""
    return CommodityMapper(config)


@pytest.fixture
def reference_time() -> datetime:
    """Fixed reference time."""
    return datetime(2026, 2, 1, 12, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def brent_watchlist_item() -> CommodityWatchlistItem:
    """Brent crude oil watchlist item."""
    return CommodityWatchlistItem({
        "symbol": "BRENT",
        "name": "Brent Crude Oil",
        "category": "energy",
        "spike_threshold_pct": 10.0,
        "zscore_threshold": 2.0,
        "impact_hint": "Fuel cost proxy for maritime shipping",
    })


def generate_stable_prices(
    base_price: float,
    days: int,
    start_date: datetime,
    volatility: float = 0.01,
) -> list[tuple[datetime, float]]:
    """Generate stable price series (no spike)."""
    prices = []
    for i in range(days):
        date = start_date - timedelta(days=days - 1 - i)
        # Slight random variation (deterministic based on day)
        variation = 1.0 + (((i * 7) % 11) - 5) * volatility / 5
        price = base_price * variation
        prices.append((date, price))
    return prices


def generate_spike_prices(
    base_price: float,
    days: int,
    start_date: datetime,
    spike_pct: float = 15.0,
) -> list[tuple[datetime, float]]:
    """Generate price series with spike at end."""
    prices = generate_stable_prices(base_price, days - 1, start_date - timedelta(days=1))
    # Add spike at the end
    spike_price = base_price * (1 + spike_pct / 100)
    prices.append((start_date, spike_price))
    return prices


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: SPIKE DETECTOR - BASIC FUNCTIONALITY
# ═══════════════════════════════════════════════════════════════════════════════

class TestSpikeDetectorBasic:
    """Tests for basic spike detection."""
    
    def test_no_spike_for_stable_series(
        self,
        spike_detector: SpikeDetector,
        brent_watchlist_item: CommodityWatchlistItem,
        reference_time: datetime,
    ):
        """Stable price series → no spike detected."""
        prices = generate_stable_prices(80.0, 30, reference_time)
        series = PriceTimeSeries(symbol="BRENT", prices=prices)
        
        result = spike_detector.detect(series, brent_watchlist_item)
        
        assert result is not None
        assert result.is_spike is False
        assert result.severity == "none"
    
    def test_spike_detected_for_significant_move(
        self,
        spike_detector: SpikeDetector,
        brent_watchlist_item: CommodityWatchlistItem,
        reference_time: datetime,
    ):
        """Large price move → spike detected."""
        prices = generate_spike_prices(80.0, 30, reference_time, spike_pct=15.0)
        series = PriceTimeSeries(symbol="BRENT", prices=prices)
        
        result = spike_detector.detect(series, brent_watchlist_item)
        
        assert result is not None
        assert result.is_spike is True
        assert result.pct_change > 10.0
        assert result.severity in ["minor", "moderate", "major"]
    
    def test_spike_direction_up(
        self,
        spike_detector: SpikeDetector,
        brent_watchlist_item: CommodityWatchlistItem,
        reference_time: datetime,
    ):
        """Positive price change → direction=up."""
        prices = generate_spike_prices(80.0, 30, reference_time, spike_pct=15.0)
        series = PriceTimeSeries(symbol="BRENT", prices=prices)
        
        result = spike_detector.detect(series, brent_watchlist_item)
        
        assert result is not None, "Expected spike to be detected"
        assert result.direction == "up"
    
    def test_spike_direction_down(
        self,
        spike_detector: SpikeDetector,
        brent_watchlist_item: CommodityWatchlistItem,
        reference_time: datetime,
    ):
        """Negative price change → direction=down."""
        prices = generate_spike_prices(80.0, 30, reference_time, spike_pct=-15.0)
        series = PriceTimeSeries(symbol="BRENT", prices=prices)
        
        result = spike_detector.detect(series, brent_watchlist_item)
        
        assert result is not None, "Expected spike to be detected"
        assert result.direction == "down"


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: SPIKE DETECTOR - DETERMINISM
# ═══════════════════════════════════════════════════════════════════════════════

class TestSpikeDetectorDeterminism:
    """Tests for deterministic spike detection."""
    
    def test_same_input_same_output(
        self,
        spike_detector: SpikeDetector,
        brent_watchlist_item: CommodityWatchlistItem,
        reference_time: datetime,
    ):
        """Same price series → same spike result."""
        prices = generate_spike_prices(80.0, 30, reference_time, spike_pct=15.0)
        
        series1 = PriceTimeSeries(symbol="BRENT", prices=prices)
        series2 = PriceTimeSeries(symbol="BRENT", prices=prices)
        
        result1 = spike_detector.detect(series1, brent_watchlist_item)
        result2 = spike_detector.detect(series2, brent_watchlist_item)
        
        assert result1 is not None, "Expected result1 to not be None"
        assert result2 is not None, "Expected result2 to not be None"
        assert result1.is_spike == result2.is_spike
        assert result1.pct_change == result2.pct_change
        assert result1.zscore == result2.zscore
        assert result1.severity == result2.severity
    
    def test_zscore_deterministic(
        self,
        spike_detector: SpikeDetector,
        brent_watchlist_item: CommodityWatchlistItem,
        reference_time: datetime,
    ):
        """Z-score calculation is deterministic."""
        prices = generate_spike_prices(80.0, 30, reference_time, spike_pct=15.0)
        series = PriceTimeSeries(symbol="BRENT", prices=prices)
        
        result1 = spike_detector.detect(series, brent_watchlist_item)
        result2 = spike_detector.detect(series, brent_watchlist_item)
        
        assert result1 is not None, "Expected result1 to not be None"
        assert result2 is not None, "Expected result2 to not be None"
        assert result1.zscore == result2.zscore


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: SPIKE DETECTOR - SEVERITY CLASSIFICATION
# ═══════════════════════════════════════════════════════════════════════════════

class TestSpikeDetectorSeverity:
    """Tests for severity classification."""
    
    def test_minor_severity(
        self,
        spike_detector: SpikeDetector,
        brent_watchlist_item: CommodityWatchlistItem,
        reference_time: datetime,
    ):
        """5-10% change → minor severity."""
        prices = generate_spike_prices(80.0, 30, reference_time, spike_pct=7.0)
        series = PriceTimeSeries(symbol="BRENT", prices=prices)
        
        result = spike_detector.detect(series, brent_watchlist_item)
        
        # Below threshold, but if zscore triggers
        if result is not None and result.is_spike:
            assert result.severity == "minor"
    
    def test_moderate_severity(
        self,
        spike_detector: SpikeDetector,
        brent_watchlist_item: CommodityWatchlistItem,
        reference_time: datetime,
    ):
        """10-20% change → moderate severity."""
        prices = generate_spike_prices(80.0, 30, reference_time, spike_pct=15.0)
        series = PriceTimeSeries(symbol="BRENT", prices=prices)
        
        result = spike_detector.detect(series, brent_watchlist_item)
        
        assert result is not None, "Expected spike to be detected"
        assert result.is_spike is True
        assert result.severity == "moderate"
    
    def test_major_severity(
        self,
        spike_detector: SpikeDetector,
        brent_watchlist_item: CommodityWatchlistItem,
        reference_time: datetime,
    ):
        """20%+ change → major severity."""
        prices = generate_spike_prices(80.0, 30, reference_time, spike_pct=25.0)
        series = PriceTimeSeries(symbol="BRENT", prices=prices)
        
        result = spike_detector.detect(series, brent_watchlist_item)
        
        assert result is not None, "Expected spike to be detected"
        assert result.is_spike is True
        assert result.severity == "major"


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: SPIKE DETECTOR - EDGE CASES
# ═══════════════════════════════════════════════════════════════════════════════

class TestSpikeDetectorEdgeCases:
    """Tests for edge cases."""
    
    def test_insufficient_data_returns_none(
        self,
        spike_detector: SpikeDetector,
        brent_watchlist_item: CommodityWatchlistItem,
        reference_time: datetime,
    ):
        """Less than min_data_points → None."""
        prices = [(reference_time - timedelta(days=i), 80.0) for i in range(5)]
        series = PriceTimeSeries(symbol="BRENT", prices=prices)
        
        result = spike_detector.detect(series, brent_watchlist_item)
        
        assert result is None
    
    def test_empty_series_returns_none(
        self,
        spike_detector: SpikeDetector,
        brent_watchlist_item: CommodityWatchlistItem,
    ):
        """Empty price series → None."""
        series = PriceTimeSeries(symbol="BRENT", prices=[])
        
        result = spike_detector.detect(series, brent_watchlist_item)
        
        assert result is None


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: SPIKE DETECTOR - CONVENIENCE FUNCTION
# ═══════════════════════════════════════════════════════════════════════════════

class TestSpikeDetectorConvenience:
    """Tests for convenience function."""
    
    def test_detect_spike_from_prices_function(
        self,
        reference_time: datetime,
    ):
        """Convenience function works correctly."""
        prices = generate_spike_prices(80.0, 30, reference_time, spike_pct=15.0)
        
        result = detect_spike_from_prices(
            prices=prices,
            symbol="BRENT",
            name="Brent Crude Oil",
            category="energy",
            spike_threshold_pct=10.0,
            zscore_threshold=2.0,
            impact_hint="Fuel cost proxy",
        )
        
        assert result is not None
        assert result.is_spike is True


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: COMMODITY MAPPER
# ═══════════════════════════════════════════════════════════════════════════════

class TestCommodityMapper:
    """Tests for mapping spikes to RawSignalEvent."""
    
    def test_valid_spike_creates_event(
        self,
        mapper: CommodityMapper,
        reference_time: datetime,
    ):
        """Valid spike creates RawSignalEvent."""
        spike = CommoditySpike(
            symbol="BRENT",
            name="Brent Crude Oil",
            category="energy",
            current_price=95.0,
            price_timestamp=reference_time,
            baseline_price=80.0,
            baseline_period_days=30,
            pct_change=18.75,
            zscore=2.5,
            is_spike=True,
            severity="moderate",
            direction="up",
            impact_hint="Fuel cost proxy for maritime shipping",
        )
        
        event = mapper.map_spike(spike, asof_ts=reference_time)
        
        assert event is not None
        # Title contains commodity name (may be formatted)
        assert "brent" in event.title.lower()
        assert event.probability > 0.0
        assert event.probability <= 0.95  # Bounded
        assert event.source_metrics is not None
        assert event.source_metrics.get('symbol') == "BRENT"
        assert event.source_metrics.get('is_spike') is True
    
    def test_non_spike_not_mapped(
        self,
        mapper: CommodityMapper,
        reference_time: datetime,
    ):
        """Non-spike data is not mapped to event."""
        spike = CommoditySpike(
            symbol="BRENT",
            name="Brent Crude Oil",
            category="energy",
            current_price=81.0,
            price_timestamp=reference_time,
            baseline_price=80.0,
            baseline_period_days=30,
            pct_change=1.25,
            zscore=0.5,
            is_spike=False,  # Not a spike
            severity="none",
            direction="up",
            impact_hint="",
        )
        
        event = mapper.map_spike(spike, asof_ts=reference_time)
        
        assert event is None
    
    def test_event_id_deterministic(
        self,
        mapper: CommodityMapper,
        reference_time: datetime,
    ):
        """Same spike → same event_id."""
        spike = CommoditySpike(
            symbol="BRENT",
            name="Brent Crude Oil",
            category="energy",
            current_price=95.0,
            price_timestamp=reference_time,
            baseline_price=80.0,
            baseline_period_days=30,
            pct_change=18.75,
            zscore=2.5,
            is_spike=True,
            severity="moderate",
            direction="up",
            impact_hint="Fuel cost proxy",
        )
        
        event1 = mapper.map_spike(spike, asof_ts=reference_time)
        event2 = mapper.map_spike(spike, asof_ts=reference_time)
        
        assert event1 is not None, "Expected event1 to be created from valid spike"
        assert event2 is not None, "Expected event2 to be created from valid spike"
        assert event1.event_id == event2.event_id
    
    def test_probability_based_on_severity(
        self,
        mapper: CommodityMapper,
        reference_time: datetime,
    ):
        """Higher severity → higher probability."""
        base_spike = {
            "symbol": "BRENT",
            "name": "Brent Crude Oil",
            "category": "energy",
            "current_price": 95.0,
            "price_timestamp": reference_time,
            "baseline_price": 80.0,
            "baseline_period_days": 30,
            "is_spike": True,
            "direction": "up",
            "impact_hint": "",
        }
        
        minor_spike = CommoditySpike(**{
            **base_spike,
            "pct_change": 8.0,
            "zscore": 1.5,
            "severity": "minor",
        })
        
        major_spike = CommoditySpike(**{
            **base_spike,
            "pct_change": 25.0,
            "zscore": 4.0,
            "severity": "major",
        })
        
        minor_event = mapper.map_spike(minor_spike, asof_ts=reference_time)
        major_event = mapper.map_spike(major_spike, asof_ts=reference_time)
        
        assert minor_event is not None, "Expected minor_event to be created"
        assert major_event is not None, "Expected major_event to be created"
        assert major_event.probability > minor_event.probability


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: COMMODITY SIGNAL SOURCE
# ═══════════════════════════════════════════════════════════════════════════════

class TestCommoditySignalSource:
    """Tests for CommoditySignalSource."""
    
    def test_mock_source_spike_scenario(self):
        """Mock source with spike scenario generates events."""
        source = MockCommoditySignalSource(scenario="spike")
        
        events = list(source.fetch_events(limit=10))
        
        # Spike scenario should produce events
        assert len(events) > 0
        for event in events:
            assert event.source_metrics is not None
            assert event.source_metrics.get('is_spike') is True
    
    def test_mock_source_normal_scenario(self):
        """Mock source with normal scenario generates no spike events."""
        source = MockCommoditySignalSource(scenario="normal")
        
        events = list(source.fetch_events(limit=10))
        
        # Normal scenario produces no spikes
        assert len(events) == 0
    
    def test_source_has_name(self):
        """Source has correct name."""
        source = create_commodity_source(scenario="spike")
        
        assert source.source_name == "commodity"
    
    def test_replay_mode_uses_cache(self):
        """Replay mode (with asof_ts) uses cached data."""
        source = MockCommoditySignalSource(scenario="spike")
        
        # First fetch (live)
        events1 = list(source.fetch_events(limit=10))
        
        # Set cache
        source.set_cached_events(events1)
        
        # Replay fetch (with asof_ts)
        reference_time = datetime.now(timezone.utc)
        events2 = list(source.fetch_events(limit=10, asof_ts=reference_time))
        
        # Should use cache
        assert len(events2) == len(events1)


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: JSON SAFETY & NO NaN
# ═══════════════════════════════════════════════════════════════════════════════

class TestNoNaNInJSON:
    """Tests for JSON safety - no NaN/Inf values."""
    
    def test_zscore_bounded(
        self,
        spike_detector: SpikeDetector,
        brent_watchlist_item: CommodityWatchlistItem,
        reference_time: datetime,
    ):
        """Z-score is bounded to prevent NaN/Inf in JSON."""
        # Create extreme price move
        prices = generate_spike_prices(80.0, 30, reference_time, spike_pct=100.0)
        series = PriceTimeSeries(symbol="BRENT", prices=prices)
        
        result = spike_detector.detect(series, brent_watchlist_item)
        
        assert result is not None
        assert -10.0 <= result.zscore <= 10.0
        assert not math.isnan(result.zscore)
        assert not math.isinf(result.zscore)
    
    def test_spike_json_serializable(
        self,
        reference_time: datetime,
    ):
        """CommoditySpike can be JSON serialized."""
        spike = CommoditySpike(
            symbol="BRENT",
            name="Brent Crude Oil",
            category="energy",
            current_price=95.0,
            price_timestamp=reference_time,
            baseline_price=80.0,
            baseline_period_days=30,
            pct_change=18.75,
            zscore=2.5,
            is_spike=True,
            severity="moderate",
            direction="up",
            impact_hint="Fuel cost",
        )
        
        # Should not raise
        json_str = spike.model_dump_json()
        
        # Verify it's valid JSON
        parsed = json.loads(json_str)
        assert parsed["symbol"] == "BRENT"
        assert parsed["zscore"] == 2.5
    
    def test_event_source_metrics_json_safe(
        self,
        mapper: CommodityMapper,
        reference_time: datetime,
    ):
        """Event source_metrics is JSON safe."""
        spike = CommoditySpike(
            symbol="BRENT",
            name="Brent Crude Oil",
            category="energy",
            current_price=95.0,
            price_timestamp=reference_time,
            baseline_price=80.0,
            baseline_period_days=30,
            pct_change=18.75,
            zscore=2.5,
            is_spike=True,
            severity="moderate",
            direction="up",
            impact_hint="Fuel cost",
        )
        
        event = mapper.map_spike(spike, asof_ts=reference_time)
        
        assert event is not None, "Expected event to be created from valid spike"
        # source_metrics should be JSON serializable
        json_str = json.dumps(event.source_metrics, default=str)
        parsed = json.loads(json_str)
        
        assert parsed["zscore"] == 2.5
        assert not any(
            isinstance(v, float) and (math.isnan(v) or math.isinf(v))
            for v in parsed.values()
            if isinstance(v, float)
        )
