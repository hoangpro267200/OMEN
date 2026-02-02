"""
Commodity Data Schemas.

Pydantic models for commodity prices and spike detection.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class CommodityPrice(BaseModel):
    """
    Single commodity price point.
    """

    symbol: str = Field(..., description="Commodity symbol (e.g., 'BRENT')")
    name: str = Field(..., description="Commodity name")
    category: str = Field(..., description="Category (energy, metals, etc.)")

    price: float = Field(..., ge=0, description="Current price")
    currency: str = Field(default="USD")
    unit: str = Field(default="barrel")

    timestamp: datetime = Field(..., description="Price timestamp")
    fetched_at: datetime = Field(..., description="When OMEN fetched this")

    # Historical context (for spike detection)
    price_1d_ago: float | None = None
    price_7d_ago: float | None = None
    price_30d_ago: float | None = None

    model_config = {"frozen": True}

    @property
    def pct_change_1d(self) -> float | None:
        """1-day percentage change."""
        if self.price_1d_ago and self.price_1d_ago > 0:
            return ((self.price - self.price_1d_ago) / self.price_1d_ago) * 100
        return None

    @property
    def pct_change_7d(self) -> float | None:
        """7-day percentage change."""
        if self.price_7d_ago and self.price_7d_ago > 0:
            return ((self.price - self.price_7d_ago) / self.price_7d_ago) * 100
        return None

    @property
    def pct_change_30d(self) -> float | None:
        """30-day percentage change."""
        if self.price_30d_ago and self.price_30d_ago > 0:
            return ((self.price - self.price_30d_ago) / self.price_30d_ago) * 100
        return None


class CommoditySpike(BaseModel):
    """
    Detected commodity price spike.

    Deterministically computed from price time series.
    """

    symbol: str
    name: str
    category: str

    # Current state
    current_price: float
    price_timestamp: datetime

    # Historical reference
    baseline_price: float = Field(..., description="Reference price for comparison")
    baseline_period_days: int = Field(..., description="Days used for baseline")

    # Spike metrics
    pct_change: float = Field(..., description="Percentage change from baseline")
    zscore: float = Field(..., description="Z-score relative to historical std")

    # Classification
    is_spike: bool = Field(..., description="Whether this qualifies as a spike")
    severity: str = Field(..., description="Spike severity: minor, moderate, major")
    direction: str = Field(..., description="up or down")

    # Impact hint
    impact_hint: str = Field(default="", description="Potential logistics impact")

    model_config = {"frozen": True}

    def to_source_metrics(self) -> dict[str, Any]:
        """Convert to source_metrics dict for RawSignalEvent."""
        return {
            "symbol": self.symbol,
            "name": self.name,
            "category": self.category,
            "current_price": self.current_price,
            "price_timestamp": self.price_timestamp.isoformat(),
            "baseline_price": self.baseline_price,
            "baseline_period_days": self.baseline_period_days,
            "pct_change": round(self.pct_change, 2),
            "zscore": round(self.zscore, 2),
            "is_spike": self.is_spike,
            "severity": self.severity,
            "direction": self.direction,
            "impact_hint": self.impact_hint,
        }


class PriceTimeSeries(BaseModel):
    """
    Historical price time series for spike detection.
    """

    symbol: str
    prices: list[tuple[datetime, float]] = Field(
        ...,
        description="List of (timestamp, price) tuples, sorted oldest to newest",
    )

    model_config = {"frozen": True}

    @property
    def latest_price(self) -> float | None:
        """Get most recent price."""
        if self.prices:
            return self.prices[-1][1]
        return None

    @property
    def latest_timestamp(self) -> datetime | None:
        """Get most recent timestamp."""
        if self.prices:
            return self.prices[-1][0]
        return None

    def get_price_n_days_ago(self, n: int) -> float | None:
        """Get price from approximately n days ago."""
        if not self.prices or not self.latest_timestamp:
            return None

        from datetime import timedelta

        target_date = self.latest_timestamp - timedelta(days=n)

        # Find closest price to target date
        closest_price = None
        closest_diff = float("inf")

        for ts, price in self.prices:
            diff = abs((ts - target_date).total_seconds())
            if diff < closest_diff:
                closest_diff = diff
                closest_price = price

        return closest_price
