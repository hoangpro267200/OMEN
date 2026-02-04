"""
Event-to-Asset Correlation Matrix.

Defines which assets should be checked when specific events occur.
This is the intelligence that makes OMEN a true Signal Intelligence Engine.

Example use cases:
- Polymarket: "War probability 70%" → Check Gold, Oil, Defense stocks
- Weather: "Hurricane Category 5" → Check Oil, Natural Gas, Freight rates
- Fed: "Rate hike decision" → Check USD, Stocks, Bonds
"""

from enum import Enum
from typing import Dict, List, Set, Optional
from dataclasses import dataclass


class EventCategory(str, Enum):
    """Categories of events that affect assets."""
    
    GEOPOLITICAL = "geopolitical"  # War, conflict, sanctions, diplomatic events
    ECONOMIC = "economic"          # Fed decisions, GDP, inflation, employment
    WEATHER = "weather"            # Hurricane, drought, flood, extreme weather
    POLITICAL = "political"        # Elections, regulations, policy changes
    MARKET = "market"              # Crashes, rallies, volatility spikes
    SUPPLY_CHAIN = "supply_chain"  # Port congestion, shipping disruptions


@dataclass(frozen=True)
class AssetCorrelation:
    """Definition of an asset correlation."""
    
    event_type: str
    assets: tuple[str, ...]
    correlation_strength: float  # 0.0 - 1.0
    description: str


class AssetCorrelationMatrix:
    """
    Defines correlation between events and assets.
    
    When event X happens, which assets Y should be checked?
    
    This matrix is used to:
    1. Automatically query related sources when a signal arrives
    2. Boost confidence when multiple sources confirm the same thesis
    3. Detect conflicts when sources disagree
    
    Usage:
        # Get assets to check when war is detected
        assets = AssetCorrelationMatrix.get_correlated_assets(
            EventCategory.GEOPOLITICAL, "war"
        )
        # Returns: ["XAU", "XAG", "CL", "DX", "defense_stocks"]
        
        # Suggest assets based on keywords
        suggestions = AssetCorrelationMatrix.suggest_assets_to_check(
            ["war", "russia", "ukraine"]
        )
        # Returns: {"war": ["XAU", "CL", ...], ...}
    """
    
    # Event type → Affected assets mapping
    CORRELATIONS: Dict[str, Dict[str, List[str]]] = {
        EventCategory.GEOPOLITICAL: {
            "war": ["XAU", "XAG", "CL", "DX", "VIX", "defense_stocks"],
            "conflict": ["XAU", "CL", "DX", "regional_currencies"],
            "sanctions": ["affected_country_currency", "energy", "commodities", "banks"],
            "tension": ["XAU", "VIX", "safe_haven_currencies"],
            "ceasefire": ["regional_stocks", "energy", "reconstruction_stocks"],
            "diplomatic": ["regional_currencies", "trade_stocks"],
        },
        EventCategory.ECONOMIC: {
            "rate_hike": ["DX", "SPY", "TLT", "bank_stocks", "growth_stocks"],
            "rate_cut": ["XAU", "growth_stocks", "emerging_markets", "real_estate"],
            "inflation": ["XAU", "TIP", "commodities", "real_estate", "TIPS"],
            "deflation": ["TLT", "bonds", "USD"],
            "gdp_report": ["SPY", "DX", "sector_etfs"],
            "employment": ["SPY", "consumer_stocks", "DX"],
            "recession": ["XAU", "TLT", "utilities", "consumer_staples", "VIX"],
        },
        EventCategory.WEATHER: {
            "hurricane_gulf": ["CL", "NG", "refinery_stocks", "insurance", "utilities"],
            "hurricane_atlantic": ["insurance", "construction", "utilities"],
            "drought": ["corn", "wheat", "soybeans", "water_utilities"],
            "flood": ["agricultural_commodities", "insurance", "construction"],
            "extreme_cold": ["NG", "heating_oil", "utilities"],
            "extreme_heat": ["NG", "utilities", "agricultural_commodities"],
            "typhoon_asia": ["shipping_stocks", "insurance", "regional_markets"],
        },
        EventCategory.POLITICAL: {
            "election": ["country_currency", "country_stocks", "VIX"],
            "regulation": ["affected_sector", "compliance_stocks"],
            "tariff": ["affected_commodities", "trade_stocks", "shipping"],
            "subsidy": ["affected_sector", "green_energy"],
            "nationalization": ["affected_company", "country_risk"],
        },
        EventCategory.MARKET: {
            "crash": ["VIX", "XAU", "TLT", "safe_haven_currencies", "puts"],
            "rally": ["growth_stocks", "risk_assets", "emerging_markets"],
            "volatility_spike": ["VIX", "options", "hedging_instruments"],
            "liquidity_crisis": ["TLT", "USD", "money_market"],
        },
        EventCategory.SUPPLY_CHAIN: {
            "port_congestion": ["shipping_stocks", "freight_rates", "affected_commodities"],
            "canal_blockage": ["shipping_stocks", "CL", "commodities"],
            "chip_shortage": ["semiconductor_stocks", "auto_stocks"],
            "container_shortage": ["shipping_stocks", "freight_rates"],
        },
    }
    
    # Keyword to event type mapping for automatic detection
    KEYWORD_MAPPINGS: Dict[str, tuple[str, str]] = {
        # Geopolitical
        "war": (EventCategory.GEOPOLITICAL, "war"),
        "conflict": (EventCategory.GEOPOLITICAL, "conflict"),
        "invasion": (EventCategory.GEOPOLITICAL, "war"),
        "military": (EventCategory.GEOPOLITICAL, "conflict"),
        "sanction": (EventCategory.GEOPOLITICAL, "sanctions"),
        "tension": (EventCategory.GEOPOLITICAL, "tension"),
        "ceasefire": (EventCategory.GEOPOLITICAL, "ceasefire"),
        # Economic
        "fed": (EventCategory.ECONOMIC, "rate_hike"),
        "rate": (EventCategory.ECONOMIC, "rate_hike"),
        "inflation": (EventCategory.ECONOMIC, "inflation"),
        "deflation": (EventCategory.ECONOMIC, "deflation"),
        "recession": (EventCategory.ECONOMIC, "recession"),
        "gdp": (EventCategory.ECONOMIC, "gdp_report"),
        "employment": (EventCategory.ECONOMIC, "employment"),
        "jobs": (EventCategory.ECONOMIC, "employment"),
        # Weather
        "hurricane": (EventCategory.WEATHER, "hurricane_gulf"),
        "typhoon": (EventCategory.WEATHER, "typhoon_asia"),
        "storm": (EventCategory.WEATHER, "hurricane_gulf"),
        "drought": (EventCategory.WEATHER, "drought"),
        "flood": (EventCategory.WEATHER, "flood"),
        "heat": (EventCategory.WEATHER, "extreme_heat"),
        "cold": (EventCategory.WEATHER, "extreme_cold"),
        # Political
        "election": (EventCategory.POLITICAL, "election"),
        "tariff": (EventCategory.POLITICAL, "tariff"),
        "regulation": (EventCategory.POLITICAL, "regulation"),
        # Market
        "crash": (EventCategory.MARKET, "crash"),
        "rally": (EventCategory.MARKET, "rally"),
        "volatility": (EventCategory.MARKET, "volatility_spike"),
        # Supply chain
        "congestion": (EventCategory.SUPPLY_CHAIN, "port_congestion"),
        "shortage": (EventCategory.SUPPLY_CHAIN, "container_shortage"),
        "blockage": (EventCategory.SUPPLY_CHAIN, "canal_blockage"),
    }
    
    @classmethod
    def get_correlated_assets(
        cls,
        event_category: EventCategory,
        event_type: str
    ) -> List[str]:
        """
        Get assets correlated with a specific event type.
        
        Args:
            event_category: Category of the event
            event_type: Specific type within the category
            
        Returns:
            List of asset symbols/names that may be affected
        """
        category_correlations = cls.CORRELATIONS.get(event_category, {})
        return category_correlations.get(event_type, [])
    
    @classmethod
    def get_all_correlated_assets(cls, event_type: str) -> Set[str]:
        """
        Search all categories for an event type.
        
        Args:
            event_type: Event type to search for
            
        Returns:
            Set of all correlated assets across categories
        """
        assets: Set[str] = set()
        for category_correlations in cls.CORRELATIONS.values():
            if event_type in category_correlations:
                assets.update(category_correlations[event_type])
        return assets
    
    @classmethod
    def suggest_assets_to_check(
        cls,
        event_keywords: List[str]
    ) -> Dict[str, List[str]]:
        """
        Given event keywords, suggest assets to check.
        
        Args:
            event_keywords: List of keywords from event description
            
        Returns:
            Dict mapping keywords to suggested assets
            
        Example:
            keywords = ["war", "russia", "ukraine"]
            suggestions = suggest_assets_to_check(keywords)
            # Returns: {"war": ["XAU", "CL", ...], ...}
        """
        suggestions: Dict[str, List[str]] = {}
        
        for keyword in event_keywords:
            keyword_lower = keyword.lower()
            
            # Check direct keyword matches
            for key, (category, event_type) in cls.KEYWORD_MAPPINGS.items():
                if key in keyword_lower:
                    assets = cls.get_correlated_assets(
                        EventCategory(category),
                        event_type
                    )
                    if assets:
                        suggestions[keyword] = assets
                    break
        
        return suggestions
    
    @classmethod
    def get_correlation_strength(
        cls,
        event_category: EventCategory,
        event_type: str,
        asset: str
    ) -> float:
        """
        Get correlation strength between an event and asset.
        
        Returns a value between 0.0 and 1.0 indicating how strongly
        the asset is correlated with the event.
        
        Note: Currently returns fixed values based on asset position
        in the list. Future versions could use historical data.
        """
        assets = cls.get_correlated_assets(event_category, event_type)
        if asset not in assets:
            return 0.0
        
        # Assets listed first are considered more correlated
        position = assets.index(asset)
        total = len(assets)
        
        # First asset = 1.0, last = 0.5
        return 1.0 - (position / total) * 0.5


# Convenience functions
def get_correlated_assets(event_category: EventCategory, event_type: str) -> List[str]:
    """Get assets correlated with an event."""
    return AssetCorrelationMatrix.get_correlated_assets(event_category, event_type)


def suggest_assets_to_check(keywords: List[str]) -> Dict[str, List[str]]:
    """Suggest assets based on event keywords."""
    return AssetCorrelationMatrix.suggest_assets_to_check(keywords)
