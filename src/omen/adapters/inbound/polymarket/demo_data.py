"""
Polymarket Demo Data - Fallback when API is blocked/unavailable.

Provides realistic logistics/geopolitical prediction market data
for demonstration purposes when network restrictions block Polymarket API.
"""

from datetime import datetime, timezone, timedelta
import random
from typing import List, Dict, Any


def get_demo_polymarket_events() -> List[Dict[str, Any]]:
    """
    Generate realistic Polymarket-style events for logistics/geopolitics.
    
    These are based on real types of prediction markets that exist on Polymarket
    but with synthetic/demo values for when the real API is unavailable.
    """
    now = datetime.now(timezone.utc)
    
    # Realistic logistics and geopolitics events
    demo_events = [
        {
            "id": "demo-red-sea-2026",
            "title": "Will Red Sea shipping disruptions continue through Q1 2026?",
            "description": "This market resolves to Yes if commercial shipping through the Red Sea and Bab-el-Mandeb strait experiences significant disruptions (>20% reduction in transit) due to Houthi attacks or related security concerns through March 31, 2026.",
            "category": "Geopolitics",
            "active": True,
            "closed": False,
            "startDate": (now - timedelta(days=30)).isoformat(),
            "endDate": (now + timedelta(days=60)).isoformat(),
            "markets": [
                {
                    "id": "demo-red-sea-yes",
                    "question": "Will Red Sea disruptions continue?",
                    "outcomes": ["Yes", "No"],
                    "outcomePrices": ["0.72", "0.28"],
                    "volume": "1250000",
                    "liquidity": "85000",
                    "lastTradePrice": "0.71",
                    "bestBid": "0.70",
                    "bestAsk": "0.73",
                }
            ],
            "tags": ["shipping", "red sea", "houthi", "yemen", "suez", "logistics"],
        },
        {
            "id": "demo-taiwan-blockade-2026",
            "title": "Will China impose any form of blockade on Taiwan in 2026?",
            "description": "This market resolves to Yes if China imposes a naval blockade, quarantine, or customs inspection zone around Taiwan that significantly impedes commercial shipping in 2026.",
            "category": "Geopolitics",
            "active": True,
            "closed": False,
            "startDate": (now - timedelta(days=60)).isoformat(),
            "endDate": (now + timedelta(days=300)).isoformat(),
            "markets": [
                {
                    "id": "demo-taiwan-blockade-yes",
                    "question": "China blockade Taiwan 2026?",
                    "outcomes": ["Yes", "No"],
                    "outcomePrices": ["0.08", "0.92"],
                    "volume": "3500000",
                    "liquidity": "220000",
                    "lastTradePrice": "0.08",
                    "bestBid": "0.07",
                    "bestAsk": "0.09",
                }
            ],
            "tags": ["taiwan", "china", "blockade", "shipping", "geopolitics"],
        },
        {
            "id": "demo-panama-drought-2026",
            "title": "Will Panama Canal reduce daily transits below 30 due to drought in Q1 2026?",
            "description": "This market resolves to Yes if the Panama Canal Authority reduces daily vessel transits to below 30 ships per day due to water levels/drought conditions at any point in Q1 2026.",
            "category": "Logistics",
            "active": True,
            "closed": False,
            "startDate": (now - timedelta(days=15)).isoformat(),
            "endDate": (now + timedelta(days=45)).isoformat(),
            "markets": [
                {
                    "id": "demo-panama-drought-yes",
                    "question": "Panama Canal below 30 transits?",
                    "outcomes": ["Yes", "No"],
                    "outcomePrices": ["0.35", "0.65"],
                    "volume": "890000",
                    "liquidity": "62000",
                    "lastTradePrice": "0.36",
                    "bestBid": "0.34",
                    "bestAsk": "0.36",
                }
            ],
            "tags": ["panama canal", "drought", "shipping", "logistics", "supply chain"],
        },
        {
            "id": "demo-oil-100-2026",
            "title": "Will Brent crude oil reach $100/barrel in Q1 2026?",
            "description": "This market resolves to Yes if Brent crude oil futures (front month contract) trade at or above $100.00 per barrel at any point before March 31, 2026.",
            "category": "Commodities",
            "active": True,
            "closed": False,
            "startDate": (now - timedelta(days=20)).isoformat(),
            "endDate": (now + timedelta(days=55)).isoformat(),
            "markets": [
                {
                    "id": "demo-oil-100-yes",
                    "question": "Brent oil $100 Q1 2026?",
                    "outcomes": ["Yes", "No"],
                    "outcomePrices": ["0.28", "0.72"],
                    "volume": "2100000",
                    "liquidity": "145000",
                    "lastTradePrice": "0.27",
                    "bestBid": "0.27",
                    "bestAsk": "0.29",
                }
            ],
            "tags": ["oil", "brent", "commodity", "energy", "prices"],
        },
        {
            "id": "demo-us-port-strike-2026",
            "title": "Will there be a major US port strike in H1 2026?",
            "description": "This market resolves to Yes if there is a work stoppage lasting more than 48 hours at any major US container port (LA, Long Beach, NY/NJ, Savannah, etc.) in the first half of 2026.",
            "category": "Logistics",
            "active": True,
            "closed": False,
            "startDate": (now - timedelta(days=45)).isoformat(),
            "endDate": (now + timedelta(days=135)).isoformat(),
            "markets": [
                {
                    "id": "demo-port-strike-yes",
                    "question": "US port strike H1 2026?",
                    "outcomes": ["Yes", "No"],
                    "outcomePrices": ["0.15", "0.85"],
                    "volume": "750000",
                    "liquidity": "48000",
                    "lastTradePrice": "0.15",
                    "bestBid": "0.14",
                    "bestAsk": "0.16",
                }
            ],
            "tags": ["port", "strike", "labor", "us", "logistics", "shipping"],
        },
        {
            "id": "demo-china-tariff-2026",
            "title": "Will US increase tariffs on Chinese goods by >10% in 2026?",
            "description": "This market resolves to Yes if the United States announces or implements a tariff increase of more than 10 percentage points on any major category of Chinese imports in 2026.",
            "category": "Trade",
            "active": True,
            "closed": False,
            "startDate": (now - timedelta(days=30)).isoformat(),
            "endDate": (now + timedelta(days=330)).isoformat(),
            "markets": [
                {
                    "id": "demo-china-tariff-yes",
                    "question": "US tariff increase on China?",
                    "outcomes": ["Yes", "No"],
                    "outcomePrices": ["0.62", "0.38"],
                    "volume": "1850000",
                    "liquidity": "125000",
                    "lastTradePrice": "0.63",
                    "bestBid": "0.61",
                    "bestAsk": "0.63",
                }
            ],
            "tags": ["tariff", "china", "us", "trade", "trade war"],
        },
        {
            "id": "demo-suez-closure-2026",
            "title": "Will Suez Canal close for >24 hours in 2026?",
            "description": "This market resolves to Yes if the Suez Canal is fully closed to vessel traffic for more than 24 consecutive hours at any point in 2026, for any reason (accident, military action, etc.).",
            "category": "Logistics",
            "active": True,
            "closed": False,
            "startDate": (now - timedelta(days=10)).isoformat(),
            "endDate": (now + timedelta(days=350)).isoformat(),
            "markets": [
                {
                    "id": "demo-suez-closure-yes",
                    "question": "Suez Canal closure 2026?",
                    "outcomes": ["Yes", "No"],
                    "outcomePrices": ["0.18", "0.82"],
                    "volume": "980000",
                    "liquidity": "72000",
                    "lastTradePrice": "0.17",
                    "bestBid": "0.17",
                    "bestAsk": "0.19",
                }
            ],
            "tags": ["suez canal", "egypt", "shipping", "logistics", "closure"],
        },
        {
            "id": "demo-russia-sanctions-2026",
            "title": "Will EU expand sanctions on Russian oil/gas in 2026?",
            "description": "This market resolves to Yes if the European Union announces new sanctions or further restrictions on Russian oil or natural gas imports in 2026.",
            "category": "Geopolitics",
            "active": True,
            "closed": False,
            "startDate": (now - timedelta(days=25)).isoformat(),
            "endDate": (now + timedelta(days=340)).isoformat(),
            "markets": [
                {
                    "id": "demo-russia-sanctions-yes",
                    "question": "EU expands Russia sanctions?",
                    "outcomes": ["Yes", "No"],
                    "outcomePrices": ["0.55", "0.45"],
                    "volume": "1420000",
                    "liquidity": "98000",
                    "lastTradePrice": "0.54",
                    "bestBid": "0.54",
                    "bestAsk": "0.56",
                }
            ],
            "tags": ["russia", "sanctions", "eu", "oil", "gas", "energy"],
        },
    ]
    
    # Add some variability to make it feel more dynamic
    for event in demo_events:
        for market in event.get("markets", []):
            # Small random price movements
            base_price = float(market["outcomePrices"][0])
            delta = random.uniform(-0.02, 0.02)
            new_price = max(0.01, min(0.99, base_price + delta))
            market["outcomePrices"][0] = f"{new_price:.2f}"
            market["outcomePrices"][1] = f"{1 - new_price:.2f}"
            market["lastTradePrice"] = f"{new_price:.2f}"
            market["bestBid"] = f"{new_price - 0.01:.2f}"
            market["bestAsk"] = f"{new_price + 0.01:.2f}"
    
    return demo_events


def is_demo_mode_active() -> bool:
    """Check if Polymarket demo mode should be active (API unavailable)."""
    import os
    import socket
    
    # Force demo mode via env var
    if os.getenv("POLYMARKET_DEMO_MODE", "").lower() in ("true", "1", "yes"):
        return True
    
    # Check if API is DNS-blocked
    try:
        ip = socket.gethostbyname("gamma-api.polymarket.com")
        if ip in ("127.0.0.1", "0.0.0.0", "::1"):
            return True
    except socket.gaierror:
        return True
    
    return False
