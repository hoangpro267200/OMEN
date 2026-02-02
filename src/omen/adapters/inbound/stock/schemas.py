"""
Stock data schemas.

Pydantic models for stock/index/forex/bond data.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class StockQuote(BaseModel):
    """Single stock/index quote."""
    
    symbol: str = Field(..., description="Ticker symbol")
    name: str = Field(default="", description="Display name")
    price: float = Field(..., description="Current/last price")
    previous_close: float = Field(default=0.0, description="Previous close price")
    change: float = Field(default=0.0, description="Price change")
    change_pct: float = Field(default=0.0, description="Percent change")
    volume: int = Field(default=0, description="Trading volume")
    timestamp: datetime = Field(..., description="Quote timestamp")
    currency: str = Field(default="USD", description="Currency")
    category: str = Field(default="stock", description="Category: stock, index, forex, bond, commodity")
    provider: str = Field(default="yfinance", description="Data provider")
    region: str = Field(default="global", description="Region: global, us, vietnam, etc.")
    
    @property
    def is_up(self) -> bool:
        """Check if price is up."""
        return self.change_pct > 0
    
    @property
    def is_significant_move(self) -> bool:
        """Check if move is significant (>2%)."""
        return abs(self.change_pct) > 2.0


class StockSpike(BaseModel):
    """Detected price spike/anomaly."""
    
    symbol: str
    name: str
    category: str
    provider: str
    region: str
    
    current_price: float
    baseline_price: float
    change_pct: float
    zscore: float
    
    severity: Literal["minor", "moderate", "major", "extreme"] = "minor"
    direction: Literal["up", "down"] = "up"
    
    detected_at: datetime
    lookback_days: int = 30
    
    impact_hint: str = ""
    
    @property
    def is_significant(self) -> bool:
        """Check if spike is significant."""
        return self.severity in ("moderate", "major", "extreme")


class StockTimeSeries(BaseModel):
    """Historical price series for a symbol."""
    
    symbol: str
    name: str
    provider: str
    
    prices: list[float] = Field(default_factory=list)
    timestamps: list[datetime] = Field(default_factory=list)
    volumes: list[int] = Field(default_factory=list)
    
    @property
    def latest_price(self) -> float | None:
        return self.prices[-1] if self.prices else None
    
    @property
    def mean_price(self) -> float:
        if not self.prices:
            return 0.0
        return sum(self.prices) / len(self.prices)
    
    @property
    def std_price(self) -> float:
        if len(self.prices) < 2:
            return 0.0
        mean = self.mean_price
        variance = sum((p - mean) ** 2 for p in self.prices) / len(self.prices)
        return variance ** 0.5
