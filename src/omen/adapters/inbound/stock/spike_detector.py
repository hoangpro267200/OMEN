"""
Stock spike detection.

Deterministic detection of significant price movements.
"""

from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Literal

from omen.adapters.inbound.stock.config import StockConfig, StockWatchlistItem
from omen.adapters.inbound.stock.schemas import StockQuote, StockSpike, StockTimeSeries


def calculate_zscore(value: float, mean: float, std: float) -> float:
    """Calculate z-score, bounded to avoid infinity."""
    if std == 0 or std < 1e-10:
        return 0.0
    
    zscore = (value - mean) / std
    
    # Bound to avoid JSON issues
    return max(-10.0, min(10.0, zscore))


def classify_severity(
    change_pct: float,
    zscore: float,
    threshold_pct: float,
) -> Literal["minor", "moderate", "major", "extreme"]:
    """Classify spike severity."""
    abs_change = abs(change_pct)
    abs_zscore = abs(zscore)
    
    # Use both percentage change and z-score
    if abs_change >= threshold_pct * 3 or abs_zscore >= 4.0:
        return "extreme"
    elif abs_change >= threshold_pct * 2 or abs_zscore >= 3.0:
        return "major"
    elif abs_change >= threshold_pct or abs_zscore >= 2.0:
        return "moderate"
    else:
        return "minor"


class SpikeDetector:
    """Detects significant price movements."""
    
    def __init__(self, config: StockConfig):
        self.config = config
    
    def detect_from_quote(
        self,
        quote: StockQuote,
        item: StockWatchlistItem,
    ) -> StockSpike | None:
        """Detect spike from a single quote (vs previous close)."""
        if quote.previous_close == 0:
            return None
        
        change_pct = quote.change_pct
        threshold = item.spike_threshold_pct
        
        # Only detect if above threshold
        if abs(change_pct) < threshold:
            return None
        
        # Simple z-score approximation (assumes ~1% daily std for most assets)
        estimated_std_pct = threshold / 2  # Conservative estimate
        zscore = calculate_zscore(change_pct, 0, estimated_std_pct)
        
        return StockSpike(
            symbol=quote.symbol,
            name=quote.name,
            category=quote.category,
            provider=quote.provider,
            region=quote.region,
            current_price=quote.price,
            baseline_price=quote.previous_close,
            change_pct=change_pct,
            zscore=zscore,
            severity=classify_severity(change_pct, zscore, threshold),
            direction="up" if change_pct > 0 else "down",
            detected_at=quote.timestamp,
            lookback_days=1,
            impact_hint=item.impact_hint,
        )
    
    def detect_from_series(
        self,
        series: StockTimeSeries,
        item: StockWatchlistItem,
    ) -> StockSpike | None:
        """Detect spike from historical series."""
        if not series.prices or len(series.prices) < self.config.lookback_days // 2:
            return None
        
        current_price = series.latest_price
        if current_price is None:
            return None
        
        mean_price = series.mean_price
        std_price = series.std_price
        
        if mean_price == 0:
            return None
        
        # Calculate change from mean
        change_pct = ((current_price - mean_price) / mean_price) * 100
        zscore = calculate_zscore(current_price, mean_price, std_price)
        
        threshold = item.spike_threshold_pct
        
        # Only detect if significant
        if abs(change_pct) < threshold and abs(zscore) < self.config.zscore_threshold:
            return None
        
        return StockSpike(
            symbol=series.symbol,
            name=series.name,
            category=item.category,
            provider=series.provider,
            region=item.region,
            current_price=current_price,
            baseline_price=mean_price,
            change_pct=change_pct,
            zscore=zscore,
            severity=classify_severity(change_pct, zscore, threshold),
            direction="up" if change_pct > 0 else "down",
            detected_at=series.timestamps[-1] if series.timestamps else datetime.now(timezone.utc),
            lookback_days=len(series.prices),
            impact_hint=item.impact_hint,
        )


def detect_spike(
    quote: StockQuote,
    item: StockWatchlistItem,
    config: StockConfig | None = None,
) -> StockSpike | None:
    """Convenience function to detect spike from quote."""
    if config is None:
        config = StockConfig()
    detector = SpikeDetector(config)
    return detector.detect_from_quote(quote, item)
