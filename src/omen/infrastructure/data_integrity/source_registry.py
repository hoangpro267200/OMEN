"""
DATA SOURCE REGISTRY - Single Source of Truth for Data Provenance

This module enforces the LIVE/DEMO data contract:
- LIVE mode MUST use REAL providers only
- MOCK providers are BLOCKED in LIVE mode
- All data sources must be explicitly classified

Usage:
    from omen.infrastructure.data_integrity.source_registry import (
        get_source_registry,
        validate_live_mode,
        SourceType,
    )
    
    # Check if LIVE mode is allowed
    can_go_live, blockers = validate_live_mode()
    if not can_go_live:
        raise RuntimeError(f"Cannot enable LIVE mode: {blockers}")
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# SOURCE CLASSIFICATION
# ═══════════════════════════════════════════════════════════════════════════

class SourceType(Enum):
    """Classification of data source providers."""
    REAL = "real"           # Live API with real data
    MOCK = "mock"           # Generated/synthetic data
    DISABLED = "disabled"   # Source is not enabled


class SourceHealth(Enum):
    """Health status of a data source."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"
    UNKNOWN = "unknown"


@dataclass
class SourceInfo:
    """Information about a data source."""
    name: str
    source_type: SourceType
    provider_name: str
    enabled: bool = True
    health: SourceHealth = SourceHealth.UNKNOWN
    last_check: Optional[datetime] = None
    config_var: Optional[str] = None
    reason: str = ""
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "source_type": self.source_type.value,
            "provider_name": self.provider_name,
            "enabled": self.enabled,
            "health": self.health.value,
            "last_check": self.last_check.isoformat() if self.last_check else None,
            "reason": self.reason,
        }


# ═══════════════════════════════════════════════════════════════════════════
# SOURCE REGISTRY
# ═══════════════════════════════════════════════════════════════════════════

class DataSourceRegistry:
    """
    Central registry for all data sources.
    
    Tracks source types, health, and enforces LIVE mode requirements.
    """
    
    def __init__(self):
        self._sources: Dict[str, SourceInfo] = {}
        self._initialized = False
        
    def initialize(self) -> None:
        """Initialize the registry by detecting all source configurations."""
        if self._initialized:
            return
            
        logger.info("Initializing Data Source Registry...")
        
        # Detect each source
        self._detect_polymarket()
        self._detect_ais()
        self._detect_weather()
        self._detect_freight()
        self._detect_news()
        self._detect_commodity()
        self._detect_stock()
        
        self._initialized = True
        
        # Log summary
        real_count = sum(1 for s in self._sources.values() if s.source_type == SourceType.REAL)
        mock_count = sum(1 for s in self._sources.values() if s.source_type == SourceType.MOCK)
        disabled_count = sum(1 for s in self._sources.values() if s.source_type == SourceType.DISABLED)
        
        logger.info(
            "Source Registry initialized: %d REAL, %d MOCK, %d DISABLED",
            real_count, mock_count, disabled_count
        )
        
    def _detect_polymarket(self) -> None:
        """Detect Polymarket source configuration."""
        api_url = os.getenv("POLYMARKET_GAMMA_API_URL", "https://gamma-api.polymarket.com")
        
        # Polymarket is always REAL (uses live Gamma API)
        self._sources["polymarket"] = SourceInfo(
            name="polymarket",
            source_type=SourceType.REAL,
            provider_name="gamma_api",
            enabled=True,
            health=SourceHealth.UNKNOWN,
            config_var="POLYMARKET_GAMMA_API_URL",
            reason="Live Gamma API endpoint configured",
        )
        
    def _detect_ais(self) -> None:
        """Detect AIS source configuration."""
        provider = os.getenv("OMEN_AIS_PROVIDER", "mock").lower()
        
        # AISStream.io support (FREE)
        aisstream_key = os.getenv("AISSTREAM_API_KEY", "").strip()
        
        # Legacy providers
        mt_key = os.getenv("OMEN_AIS_MARINETRAFFIC_API_KEY", "")
        aishub_user = os.getenv("OMEN_AIS_AISHUB_USERNAME", "")
        
        if provider == "aisstream" and aisstream_key and len(aisstream_key) >= 10:
            source_type = SourceType.REAL
            reason = "AISStream.io WebSocket configured (FREE)"
            provider_name = "aisstream"
        elif provider == "marinetraffic" and mt_key:
            source_type = SourceType.REAL
            reason = "MarineTraffic API key configured"
            provider_name = "marinetraffic"
        elif provider == "aishub" and aishub_user:
            source_type = SourceType.REAL
            reason = "AISHub credentials configured"
            provider_name = "aishub"
        elif provider == "mock":
            source_type = SourceType.MOCK
            reason = "Using mock data (OMEN_AIS_PROVIDER=mock)"
            provider_name = "mock"
        else:
            source_type = SourceType.MOCK
            reason = f"Provider '{provider}' configured but no API credentials"
            provider_name = provider
            
        self._sources["ais"] = SourceInfo(
            name="ais",
            source_type=source_type,
            provider_name=provider_name,
            enabled=True,
            health=SourceHealth.UNKNOWN,
            config_var="OMEN_AIS_PROVIDER",
            reason=reason,
        )
        
    def _detect_weather(self) -> None:
        """Detect Weather source configuration."""
        provider = os.getenv("OMEN_WEATHER_PROVIDER", "openmeteo").lower()
        ow_key = os.getenv("OMEN_WEATHER_OPENWEATHER_API_KEY", "")
        
        # Open-Meteo is FREE and doesn't require an API key
        if provider == "openmeteo":
            source_type = SourceType.REAL
            reason = "Open-Meteo API (FREE, no key required)"
            provider_name = "openmeteo"
        elif provider == "openweather" and ow_key:
            source_type = SourceType.REAL
            reason = "OpenWeather API key configured"
            provider_name = "openweather"
        elif provider == "mock":
            source_type = SourceType.MOCK
            reason = "Using mock data (OMEN_WEATHER_PROVIDER=mock)"
            provider_name = "mock"
        else:
            source_type = SourceType.MOCK
            reason = f"Provider '{provider}' configured but not implemented"
            provider_name = provider
            
        self._sources["weather"] = SourceInfo(
            name="weather",
            source_type=source_type,
            provider_name=provider_name,
            enabled=True,
            health=SourceHealth.UNKNOWN,
            config_var="OMEN_WEATHER_PROVIDER",
            reason=reason,
        )
        
    def _detect_freight(self) -> None:
        """Detect Freight source configuration."""
        provider = os.getenv("OMEN_FREIGHT_PROVIDER", "fbx").lower()
        
        # FBX uses public data + ETF proxies (FREE)
        if provider == "fbx":
            source_type = SourceType.REAL
            reason = "Freightos Baltic Index (public data + ETF proxy)"
            provider_name = "fbx"
        elif provider in ("freightos", "xeneta", "drewry"):
            api_key = os.getenv("OMEN_FREIGHT_API_KEY", "").strip()
            if api_key and len(api_key) >= 10:
                source_type = SourceType.REAL
                reason = f"{provider} API configured"
                provider_name = provider
            else:
                source_type = SourceType.MOCK
                reason = f"{provider} API key missing"
                provider_name = provider
        elif provider == "mock":
            source_type = SourceType.MOCK
            reason = "Using mock data (OMEN_FREIGHT_PROVIDER=mock)"
            provider_name = "mock"
        else:
            source_type = SourceType.MOCK
            reason = f"Unknown freight provider: {provider}"
            provider_name = provider
            
        self._sources["freight"] = SourceInfo(
            name="freight",
            source_type=source_type,
            provider_name=provider_name,
            enabled=True,
            health=SourceHealth.UNKNOWN,
            config_var="OMEN_FREIGHT_PROVIDER",
            reason=reason,
        )
        
    def _detect_news(self) -> None:
        """Detect News source configuration."""
        # Check NewsData.io first (preferred, FREE 200/day)
        newsdata_key = os.getenv("NEWSDATA_API_KEY", "").strip()
        if newsdata_key and len(newsdata_key) >= 10:
            self._sources["news"] = SourceInfo(
                name="news",
                source_type=SourceType.REAL,
                provider_name="newsdata",
                enabled=True,
                health=SourceHealth.UNKNOWN,
                config_var="NEWSDATA_API_KEY",
                reason="NewsData.io API configured (FREE 200/day)",
            )
            return
        
        # Fallback to NewsAPI
        newsapi_key = os.getenv("NEWS_API_KEY", "").strip()
        if newsapi_key and len(newsapi_key) >= 10:
            self._sources["news"] = SourceInfo(
                name="news",
                source_type=SourceType.REAL,
                provider_name="newsapi",
                enabled=True,
                health=SourceHealth.UNKNOWN,
                config_var="NEWS_API_KEY",
                reason="NewsAPI key configured",
            )
            return
        
        # Check explicit provider setting
        provider = os.getenv("NEWS_PROVIDER", "").lower()
        if provider == "mock":
            self._sources["news"] = SourceInfo(
                name="news",
                source_type=SourceType.MOCK,
                provider_name="mock",
                enabled=True,
                health=SourceHealth.UNKNOWN,
                config_var="NEWS_PROVIDER",
                reason="Using mock data (NEWS_PROVIDER=mock)",
            )
            return
            
        # No API key detected
        self._sources["news"] = SourceInfo(
            name="news",
            source_type=SourceType.MOCK,
            provider_name="mock",
            enabled=True,
            health=SourceHealth.UNKNOWN,
            config_var="NEWSDATA_API_KEY",
            reason="No news API key detected (set NEWSDATA_API_KEY or NEWS_API_KEY)",
        )
        
    def _detect_commodity(self) -> None:
        """Detect Commodity source configuration."""
        provider = os.getenv("COMMODITY_PROVIDER", "alphavantage")
        api_key = os.getenv("ALPHAVANTAGE_API_KEY", "")
        
        if provider == "alphavantage" and api_key:
            source_type = SourceType.REAL
            reason = "AlphaVantage API key configured"
        elif provider == "mock":
            source_type = SourceType.MOCK
            reason = "Using mock data (COMMODITY_PROVIDER=mock)"
        else:
            source_type = SourceType.MOCK
            reason = f"Provider '{provider}' configured but no API key"
            
        self._sources["commodity"] = SourceInfo(
            name="commodity",
            source_type=source_type,
            provider_name=provider,
            enabled=True,
            health=SourceHealth.UNKNOWN,
            config_var="ALPHAVANTAGE_API_KEY",
            reason=reason,
        )
        
    def _detect_stock(self) -> None:
        """Detect Stock source configuration."""
        provider = os.getenv("STOCK_PROVIDER", "both")
        
        if provider in ("yfinance", "vnstock", "both"):
            source_type = SourceType.REAL
            reason = f"Using real stock API(s): {provider}"
        elif provider == "mock":
            source_type = SourceType.MOCK
            reason = "Using mock data (STOCK_PROVIDER=mock)"
        else:
            source_type = SourceType.REAL
            reason = f"Unknown provider '{provider}', defaulting to yfinance"
            
        self._sources["stock"] = SourceInfo(
            name="stock",
            source_type=source_type,
            provider_name=provider,
            enabled=True,
            health=SourceHealth.UNKNOWN,
            config_var="STOCK_PROVIDER",
            reason=reason,
        )
        
    def get_all_sources(self) -> List[SourceInfo]:
        """Get all registered sources."""
        self.initialize()
        return list(self._sources.values())
        
    def get_source(self, name: str) -> Optional[SourceInfo]:
        """Get a specific source by name."""
        self.initialize()
        return self._sources.get(name)
        
    def get_mock_sources(self) -> List[SourceInfo]:
        """Get all sources currently using mock data."""
        self.initialize()
        return [s for s in self._sources.values() if s.source_type == SourceType.MOCK]
        
    def get_real_sources(self) -> List[SourceInfo]:
        """Get all sources using real data."""
        self.initialize()
        return [s for s in self._sources.values() if s.source_type == SourceType.REAL]
        
    def validate_live_mode(self) -> Tuple[bool, List[str]]:
        """
        Validate if LIVE mode can be enabled.
        
        Returns:
            Tuple of (can_go_live, list_of_blockers)
        """
        self.initialize()
        
        blockers = []
        mock_sources = self.get_mock_sources()
        
        for source in mock_sources:
            if source.enabled:
                blockers.append(
                    f"{source.name}: {source.reason}"
                )
                
        can_go_live = len(blockers) == 0
        return can_go_live, blockers
        
    def get_live_mode_status(self) -> dict:
        """Get detailed status for LIVE mode validation."""
        self.initialize()
        can_go_live, blockers = self.validate_live_mode()
        
        return {
            "can_go_live": can_go_live,
            "blockers": blockers,
            "sources": {
                name: info.to_dict() 
                for name, info in self._sources.items()
            },
            "summary": {
                "real_count": len(self.get_real_sources()),
                "mock_count": len(self.get_mock_sources()),
                "total": len(self._sources),
            },
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }


# ═══════════════════════════════════════════════════════════════════════════
# GLOBAL INSTANCE
# ═══════════════════════════════════════════════════════════════════════════

_registry: Optional[DataSourceRegistry] = None


def get_source_registry() -> DataSourceRegistry:
    """Get the global source registry instance."""
    global _registry
    if _registry is None:
        _registry = DataSourceRegistry()
    return _registry


def validate_live_mode() -> Tuple[bool, List[str]]:
    """
    Convenience function to validate LIVE mode.
    
    Returns:
        Tuple of (can_go_live, list_of_blockers)
    """
    return get_source_registry().validate_live_mode()


def require_live_mode() -> None:
    """
    Raise an error if LIVE mode requirements are not met.
    
    Use this at startup or when switching to LIVE mode.
    """
    can_go_live, blockers = validate_live_mode()
    if not can_go_live:
        error_msg = "LIVE MODE BLOCKED - Mock data sources detected:\n"
        error_msg += "\n".join(f"  - {b}" for b in blockers)
        error_msg += "\n\nTo enable LIVE mode, configure real API providers for all sources."
        raise RuntimeError(error_msg)


def refresh_registry() -> None:
    """
    Force refresh the source registry.
    
    Useful after environment variables change.
    """
    global _registry
    _registry = DataSourceRegistry()
    _registry.initialize()
