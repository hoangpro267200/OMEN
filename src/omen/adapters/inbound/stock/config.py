"""
Stock adapter configuration.

Supports:
- yfinance: Global markets (stocks, indices, forex, commodities, bonds)
- vnstock: Vietnamese stocks and indices
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings


def _load_yaml_config() -> dict[str, Any]:
    """Load stock.yaml configuration file."""
    config_path = Path(__file__).parent.parent.parent.parent / "config" / "stock.yaml"
    if config_path.exists():
        with open(config_path, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}


_YAML_CONFIG = _load_yaml_config()


class StockWatchlistItem:
    """Single item in the stock watchlist."""

    def __init__(self, data: dict[str, Any]):
        self.symbol: str = data.get("symbol", "")
        self.name: str = data.get("name", "")
        self.category: str = data.get("category", "stock")
        self.provider: str = data.get("provider", "yfinance")
        self.yf_symbol: str = data.get("yf_symbol", self.symbol)
        self.vn_symbol: str = data.get("vn_symbol", "")
        self.currency: str = data.get("currency", "USD")
        self.spike_threshold_pct: float = data.get("spike_threshold_pct", 3.0)
        self.impact_hint: str = data.get("impact_hint", "")
        self.region: str = data.get("region", "global")


class StockConfig(BaseSettings):
    """
    Stock source configuration.

    Loads from:
    1. Environment variables (STOCK_*)
    2. stock.yaml config file
    """

    # Provider selection
    provider: Literal["yfinance", "vnstock", "both", "mock"] = Field(
        default="both",
        description="Stock provider: 'yfinance', 'vnstock', 'both', or 'mock'",
    )

    # Enable/disable specific providers
    enable_yfinance: bool = Field(default=True)
    enable_vnstock: bool = Field(default=True)

    # Timeouts and retries
    timeout_seconds: float = Field(
        default=_YAML_CONFIG.get("settings", {}).get("timeout_seconds", 30.0),
    )
    retry_attempts: int = Field(
        default=_YAML_CONFIG.get("settings", {}).get("retry_attempts", 3),
    )
    retry_backoff_seconds: float = Field(
        default=_YAML_CONFIG.get("settings", {}).get("retry_backoff_seconds", 1.0),
    )

    # Data parameters
    lookback_days: int = Field(
        default=_YAML_CONFIG.get("settings", {}).get("lookback_days", 30),
    )

    # Spike detection
    default_spike_threshold_pct: float = Field(
        default=_YAML_CONFIG.get("spike_detection", {}).get("default_threshold_pct", 3.0),
    )
    zscore_threshold: float = Field(
        default=_YAML_CONFIG.get("spike_detection", {}).get("zscore_threshold", 2.0),
    )

    # Scoring
    max_confidence_boost: float = Field(
        default=_YAML_CONFIG.get("scoring", {}).get("max_confidence_boost", 0.10),
    )

    model_config = {
        "env_prefix": "STOCK_",
        "env_file": ".env",
        "extra": "ignore",
    }

    def get_watchlist(self) -> list[StockWatchlistItem]:
        """Load watchlist from YAML config."""
        watchlist_data = _YAML_CONFIG.get("watchlist", [])
        if not watchlist_data:
            # Default watchlist if no YAML
            watchlist_data = DEFAULT_WATCHLIST
        return [StockWatchlistItem(item) for item in watchlist_data]

    def get_vn_watchlist(self) -> list[StockWatchlistItem]:
        """Get only Vietnamese stocks from watchlist."""
        return [w for w in self.get_watchlist() if w.provider == "vnstock" or w.region == "vietnam"]

    def get_global_watchlist(self) -> list[StockWatchlistItem]:
        """Get only global stocks from watchlist."""
        return [w for w in self.get_watchlist() if w.provider == "yfinance"]


# Default watchlist when no YAML config
DEFAULT_WATCHLIST = [
    # === GLOBAL INDICES ===
    {
        "symbol": "SPX",
        "name": "S&P 500",
        "yf_symbol": "^GSPC",
        "category": "index",
        "provider": "yfinance",
        "region": "us",
        "spike_threshold_pct": 2.0,
        "impact_hint": "US market sentiment",
    },
    {
        "symbol": "NDX",
        "name": "NASDAQ 100",
        "yf_symbol": "^NDX",
        "category": "index",
        "provider": "yfinance",
        "region": "us",
        "spike_threshold_pct": 2.5,
        "impact_hint": "Tech sector sentiment",
    },
    {
        "symbol": "DJI",
        "name": "Dow Jones",
        "yf_symbol": "^DJI",
        "category": "index",
        "provider": "yfinance",
        "region": "us",
        "spike_threshold_pct": 2.0,
        "impact_hint": "Industrial sentiment",
    },
    {
        "symbol": "VIX",
        "name": "Volatility Index",
        "yf_symbol": "^VIX",
        "category": "volatility",
        "provider": "yfinance",
        "region": "us",
        "spike_threshold_pct": 15.0,
        "impact_hint": "Market fear gauge",
    },
    # === FOREX / CURRENCIES ===
    {
        "symbol": "DXY",
        "name": "US Dollar Index",
        "yf_symbol": "DX-Y.NYB",
        "category": "forex",
        "provider": "yfinance",
        "region": "global",
        "spike_threshold_pct": 1.0,
        "impact_hint": "USD strength",
    },
    {
        "symbol": "EURUSD",
        "name": "EUR/USD",
        "yf_symbol": "EURUSD=X",
        "category": "forex",
        "provider": "yfinance",
        "region": "global",
        "spike_threshold_pct": 1.0,
        "impact_hint": "Euro strength",
    },
    {
        "symbol": "USDJPY",
        "name": "USD/JPY",
        "yf_symbol": "JPY=X",
        "category": "forex",
        "provider": "yfinance",
        "region": "global",
        "spike_threshold_pct": 1.5,
        "impact_hint": "Yen carry trade",
    },
    {
        "symbol": "USDVND",
        "name": "USD/VND",
        "yf_symbol": "VND=X",
        "category": "forex",
        "provider": "yfinance",
        "region": "vietnam",
        "spike_threshold_pct": 0.5,
        "impact_hint": "VND exchange rate",
    },
    # === BONDS / YIELDS ===
    {
        "symbol": "US10Y",
        "name": "US 10Y Treasury",
        "yf_symbol": "^TNX",
        "category": "bond",
        "provider": "yfinance",
        "region": "us",
        "spike_threshold_pct": 5.0,
        "impact_hint": "Risk-free rate benchmark",
    },
    {
        "symbol": "US2Y",
        "name": "US 2Y Treasury",
        "yf_symbol": "^IRX",
        "category": "bond",
        "provider": "yfinance",
        "region": "us",
        "spike_threshold_pct": 5.0,
        "impact_hint": "Short-term rates",
    },
    # === COMMODITIES (bổ sung cho AlphaVantage) ===
    {
        "symbol": "GOLD",
        "name": "Gold",
        "yf_symbol": "GC=F",
        "category": "commodity",
        "provider": "yfinance",
        "region": "global",
        "spike_threshold_pct": 2.0,
        "impact_hint": "Safe haven demand",
    },
    {
        "symbol": "SILVER",
        "name": "Silver",
        "yf_symbol": "SI=F",
        "category": "commodity",
        "provider": "yfinance",
        "region": "global",
        "spike_threshold_pct": 3.0,
        "impact_hint": "Industrial + safe haven",
    },
    {
        "symbol": "CRUDE",
        "name": "WTI Crude Oil",
        "yf_symbol": "CL=F",
        "category": "commodity",
        "provider": "yfinance",
        "region": "global",
        "spike_threshold_pct": 4.0,
        "impact_hint": "Energy costs",
    },
    {
        "symbol": "BRENT",
        "name": "Brent Crude",
        "yf_symbol": "BZ=F",
        "category": "commodity",
        "provider": "yfinance",
        "region": "global",
        "spike_threshold_pct": 4.0,
        "impact_hint": "Global oil benchmark",
    },
    {
        "symbol": "NATGAS",
        "name": "Natural Gas",
        "yf_symbol": "NG=F",
        "category": "commodity",
        "provider": "yfinance",
        "region": "global",
        "spike_threshold_pct": 5.0,
        "impact_hint": "Energy/heating costs",
    },
    {
        "symbol": "COPPER",
        "name": "Copper",
        "yf_symbol": "HG=F",
        "category": "commodity",
        "provider": "yfinance",
        "region": "global",
        "spike_threshold_pct": 3.0,
        "impact_hint": "Industrial demand indicator",
    },
    # === VIETNAM INDICES ===
    {
        "symbol": "VNINDEX",
        "name": "VN-Index",
        "vn_symbol": "VNINDEX",
        "category": "index",
        "provider": "vnstock",
        "region": "vietnam",
        "currency": "VND",
        "spike_threshold_pct": 2.0,
        "impact_hint": "VN market sentiment",
    },
    {
        "symbol": "VN30",
        "name": "VN30 Index",
        "vn_symbol": "VN30",
        "category": "index",
        "provider": "vnstock",
        "region": "vietnam",
        "currency": "VND",
        "spike_threshold_pct": 2.5,
        "impact_hint": "VN blue chips",
    },
    {
        "symbol": "HNX",
        "name": "HNX Index",
        "vn_symbol": "HNX",
        "category": "index",
        "provider": "vnstock",
        "region": "vietnam",
        "currency": "VND",
        "spike_threshold_pct": 3.0,
        "impact_hint": "VN small/mid caps",
    },
    # === VIETNAM STOCKS (Top companies) ===
    {
        "symbol": "VNM",
        "name": "Vinamilk",
        "vn_symbol": "VNM",
        "category": "stock",
        "provider": "vnstock",
        "region": "vietnam",
        "currency": "VND",
        "spike_threshold_pct": 4.0,
        "impact_hint": "Consumer sector",
    },
    {
        "symbol": "VIC",
        "name": "Vingroup",
        "vn_symbol": "VIC",
        "category": "stock",
        "provider": "vnstock",
        "region": "vietnam",
        "currency": "VND",
        "spike_threshold_pct": 4.0,
        "impact_hint": "Real estate/conglomerate",
    },
    {
        "symbol": "VHM",
        "name": "Vinhomes",
        "vn_symbol": "VHM",
        "category": "stock",
        "provider": "vnstock",
        "region": "vietnam",
        "currency": "VND",
        "spike_threshold_pct": 4.0,
        "impact_hint": "Real estate",
    },
    {
        "symbol": "VCB",
        "name": "Vietcombank",
        "vn_symbol": "VCB",
        "category": "stock",
        "provider": "vnstock",
        "region": "vietnam",
        "currency": "VND",
        "spike_threshold_pct": 3.0,
        "impact_hint": "Banking sector",
    },
    {
        "symbol": "FPT",
        "name": "FPT Corp",
        "vn_symbol": "FPT",
        "category": "stock",
        "provider": "vnstock",
        "region": "vietnam",
        "currency": "VND",
        "spike_threshold_pct": 4.0,
        "impact_hint": "Tech sector VN",
    },
    {
        "symbol": "HPG",
        "name": "Hoa Phat",
        "vn_symbol": "HPG",
        "category": "stock",
        "provider": "vnstock",
        "region": "vietnam",
        "currency": "VND",
        "spike_threshold_pct": 4.0,
        "impact_hint": "Steel/manufacturing",
    },
    {
        "symbol": "MSN",
        "name": "Masan Group",
        "vn_symbol": "MSN",
        "category": "stock",
        "provider": "vnstock",
        "region": "vietnam",
        "currency": "VND",
        "spike_threshold_pct": 4.0,
        "impact_hint": "Consumer/retail",
    },
    {
        "symbol": "MWG",
        "name": "Mobile World",
        "vn_symbol": "MWG",
        "category": "stock",
        "provider": "vnstock",
        "region": "vietnam",
        "currency": "VND",
        "spike_threshold_pct": 4.0,
        "impact_hint": "Retail sector",
    },
]
