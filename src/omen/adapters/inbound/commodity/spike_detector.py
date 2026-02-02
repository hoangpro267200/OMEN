"""
Commodity Spike Detector.

Deterministically detects price spikes from time series data.

Key principles:
- Deterministic: Same input = same output
- No randomness or external state
- Config-driven thresholds
"""

from __future__ import annotations

import math
from datetime import datetime

from .config import CommodityConfig, CommodityWatchlistItem
from .schemas import PriceTimeSeries, CommoditySpike


class SpikeDetector:
    """
    Deterministic spike detection from price time series.
    
    Methods:
    - Percentage change from baseline
    - Z-score relative to historical volatility
    - Severity classification
    """
    
    def __init__(self, config: CommodityConfig | None = None):
        self._config = config or CommodityConfig()
        self._severity_levels = self._config.get_severity_levels()
    
    def detect(
        self,
        series: PriceTimeSeries,
        watchlist_item: CommodityWatchlistItem,
    ) -> CommoditySpike | None:
        """
        Detect spike in price time series.
        
        Args:
            series: Historical price data
            watchlist_item: Configuration for this commodity
        
        Returns:
            CommoditySpike if spike detected, None otherwise
        """
        # Validate data quality
        if len(series.prices) < self._config.min_data_points:
            return None
        
        latest_price = series.latest_price
        latest_ts = series.latest_timestamp
        
        if latest_price is None or latest_ts is None:
            return None
        
        # Calculate baseline (average of lookback period)
        baseline_price = self._calculate_baseline(series)
        if baseline_price is None or baseline_price <= 0:
            return None
        
        # Calculate percentage change
        pct_change = ((latest_price - baseline_price) / baseline_price) * 100
        
        # Calculate z-score
        zscore = self._calculate_zscore(series, latest_price)
        
        # Determine if this is a spike
        is_spike = self._is_spike(
            pct_change=pct_change,
            zscore=zscore,
            threshold_pct=watchlist_item.spike_threshold_pct,
            threshold_zscore=watchlist_item.zscore_threshold,
        )
        
        # Classify severity
        severity = self._classify_severity(abs(pct_change))
        direction = "up" if pct_change > 0 else "down"
        
        return CommoditySpike(
            symbol=watchlist_item.symbol,
            name=watchlist_item.name,
            category=watchlist_item.category,
            current_price=latest_price,
            price_timestamp=latest_ts,
            baseline_price=baseline_price,
            baseline_period_days=self._config.lookback_days,
            pct_change=pct_change,
            zscore=zscore,
            is_spike=is_spike,
            severity=severity if is_spike else "none",
            direction=direction,
            impact_hint=watchlist_item.impact_hint,
        )
    
    def _calculate_baseline(self, series: PriceTimeSeries) -> float | None:
        """
        Calculate baseline price from lookback period.
        
        Uses simple moving average for stability.
        """
        if not series.prices:
            return None
        
        # Get prices from lookback period
        # Exclude most recent N days (smoothing window) to avoid self-reference
        exclude_recent = self._config.smoothing_window
        
        if len(series.prices) <= exclude_recent:
            return None
        
        lookback_prices = [p for _, p in series.prices[:-exclude_recent]]
        
        if not lookback_prices:
            return None
        
        # Simple moving average
        return sum(lookback_prices) / len(lookback_prices)
    
    def _calculate_zscore(
        self,
        series: PriceTimeSeries,
        current_price: float,
    ) -> float:
        """
        Calculate z-score of current price.
        
        z = (current - mean) / std
        
        Uses rolling window if configured.
        """
        if len(series.prices) < self._config.min_data_points:
            return 0.0
        
        prices = [p for _, p in series.prices]
        
        # Calculate mean and std
        mean = sum(prices) / len(prices)
        variance = sum((p - mean) ** 2 for p in prices) / len(prices)
        std = math.sqrt(variance) if variance > 0 else 1.0
        
        # Avoid division by zero
        if std < 0.0001:
            return 0.0
        
        zscore = (current_price - mean) / std
        
        # Cap extreme values for safety
        return max(-10.0, min(10.0, zscore))
    
    def _is_spike(
        self,
        pct_change: float,
        zscore: float,
        threshold_pct: float,
        threshold_zscore: float,
    ) -> bool:
        """
        Determine if price movement qualifies as a spike.
        
        Spike = (|pct_change| > threshold_pct) OR (|zscore| > threshold_zscore)
        """
        return abs(pct_change) >= threshold_pct or abs(zscore) >= threshold_zscore
    
    def _classify_severity(self, abs_pct_change: float) -> str:
        """Classify spike severity based on percentage change."""
        for severity, bounds in self._severity_levels.items():
            min_pct = bounds.get("min_pct", 0)
            max_pct = bounds.get("max_pct")
            
            if min_pct is None:
                min_pct = 0
            
            if abs_pct_change >= min_pct:
                if max_pct is None or abs_pct_change < max_pct:
                    return severity
        
        return "minor"


def detect_spike_from_prices(
    prices: list[tuple[datetime, float]],
    symbol: str,
    name: str,
    category: str,
    spike_threshold_pct: float = 10.0,
    zscore_threshold: float = 2.0,
    impact_hint: str = "",
) -> CommoditySpike | None:
    """
    Convenience function to detect spike from price list.
    
    Args:
        prices: List of (timestamp, price) tuples
        symbol: Commodity symbol
        name: Commodity name
        category: Commodity category
        spike_threshold_pct: Percentage change threshold
        zscore_threshold: Z-score threshold
        impact_hint: Impact description
    
    Returns:
        CommoditySpike if detected, None otherwise
    """
    from .config import CommodityWatchlistItem
    
    series = PriceTimeSeries(symbol=symbol, prices=prices)
    
    watchlist_item = CommodityWatchlistItem({
        "symbol": symbol,
        "name": name,
        "category": category,
        "spike_threshold_pct": spike_threshold_pct,
        "zscore_threshold": zscore_threshold,
        "impact_hint": impact_hint,
    })
    
    detector = SpikeDetector()
    return detector.detect(series, watchlist_item)
