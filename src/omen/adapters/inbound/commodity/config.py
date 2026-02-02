"""
Commodity Source Configuration.

Loads from environment variables and YAML config file.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings


def _load_yaml_config() -> dict[str, Any]:
    """Load commodities.yaml configuration file."""
    config_path = Path(__file__).parent.parent.parent.parent / "config" / "commodities.yaml"
    if config_path.exists():
        with open(config_path, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}


_YAML_CONFIG = _load_yaml_config()


class CommodityWatchlistItem:
    """Single commodity in the watchlist."""

    def __init__(self, data: dict[str, Any]):
        self.symbol: str = data.get("symbol", "")
        self.name: str = data.get("name", "")
        self.category: str = data.get("category", "other")
        self.provider: str = data.get("provider", "alphavantage")
        self.alphavantage_symbol: str = data.get("alphavantage_symbol", self.symbol)
        self.unit: str = data.get("unit", "USD")
        self.spike_threshold_pct: float = data.get("spike_threshold_pct", 10.0)
        self.zscore_threshold: float = data.get("zscore_threshold", 2.0)
        self.impact_hint: str = data.get("impact_hint", "")


class CommodityConfig(BaseSettings):
    """
    Commodity source configuration.

    Loads from:
    1. Environment variables (COMMODITY_* or ALPHAVANTAGE_*)
    2. commodities.yaml config file
    """

    # Provider selection
    provider: str = Field(
        default="alphavantage",
        description="Price provider: 'alphavantage', 'eia', or 'mock'",
    )

    # AlphaVantage settings
    alphavantage_api_key: str = Field(
        default="",
        alias="ALPHAVANTAGE_API_KEY",
        description="AlphaVantage API key",
    )
    alphavantage_base_url: str = Field(
        default="https://www.alphavantage.co/query",
    )

    # EIA settings (optional)
    eia_api_key: str = Field(
        default="",
        alias="EIA_API_KEY",
        description="EIA API key",
    )

    # Timeouts and retries
    timeout_seconds: float = Field(
        default=_YAML_CONFIG.get("providers", {})
        .get("alphavantage", {})
        .get("timeout_seconds", 15.0),
    )
    retry_attempts: int = Field(
        default=_YAML_CONFIG.get("providers", {}).get("alphavantage", {}).get("retry_attempts", 3),
    )
    retry_backoff_seconds: float = Field(
        default=_YAML_CONFIG.get("providers", {})
        .get("alphavantage", {})
        .get("retry_backoff_seconds", 2.0),
    )
    rate_limit_per_minute: int = Field(
        default=_YAML_CONFIG.get("providers", {})
        .get("alphavantage", {})
        .get("rate_limit_per_minute", 5),
    )

    # Spike detection parameters
    lookback_days: int = Field(
        default=_YAML_CONFIG.get("spike_detection", {}).get("lookback_days", 30),
    )
    min_data_points: int = Field(
        default=_YAML_CONFIG.get("spike_detection", {}).get("min_data_points", 20),
    )
    smoothing_window: int = Field(
        default=_YAML_CONFIG.get("spike_detection", {}).get("smoothing_window", 3),
    )

    # Data quality
    max_staleness_hours: int = Field(
        default=_YAML_CONFIG.get("data_quality", {}).get("max_staleness_hours", 24),
    )
    max_daily_change_pct: float = Field(
        default=_YAML_CONFIG.get("data_quality", {}).get("max_daily_change_pct", 50.0),
    )

    # Scoring
    max_confidence_boost: float = Field(
        default=_YAML_CONFIG.get("scoring", {}).get("max_confidence_boost", 0.08),
    )

    model_config = {
        "env_prefix": "COMMODITY_",
        "env_file": ".env",
        "extra": "ignore",
    }

    def get_watchlist(self) -> list[CommodityWatchlistItem]:
        """Load watchlist from YAML config."""
        watchlist_data = _YAML_CONFIG.get("watchlist", [])
        return [CommodityWatchlistItem(item) for item in watchlist_data]

    def get_severity_levels(self) -> dict[str, dict[str, float | None]]:
        """Load severity level thresholds."""
        return _YAML_CONFIG.get("spike_detection", {}).get(
            "severity_levels",
            {
                "minor": {"min_pct": 5.0, "max_pct": 10.0},
                "moderate": {"min_pct": 10.0, "max_pct": 20.0},
                "major": {"min_pct": 20.0, "max_pct": None},
            },
        )

    def get_category_weights(self) -> dict[str, float]:
        """Load category weights for scoring."""
        return _YAML_CONFIG.get("scoring", {}).get(
            "category_weights",
            {
                "energy": 1.0,
                "metals": 0.7,
                "agricultural": 0.5,
            },
        )
