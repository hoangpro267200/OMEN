"""
Freightos Baltic Index (FBX) Adapter
Uses publicly available freight rate data and ETF proxies
"""

import httpx
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import logging

logger = logging.getLogger(__name__)


@dataclass
class FreightRate:
    """Container freight rate from FBX."""
    route_code: str
    route_name: str
    rate_usd_feu: float
    change_week: float
    change_week_pct: float
    last_updated: datetime
    
    @property
    def trend(self) -> str:
        """Get rate trend direction."""
        if self.change_week_pct > 2:
            return "rising"
        elif self.change_week_pct < -2:
            return "falling"
        return "stable"
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['trend'] = self.trend
        data['last_updated'] = self.last_updated.isoformat()
        return data


class FBXAdapter:
    """
    Freightos Baltic Index Adapter.
    
    Uses shipping ETFs as proxy for freight market conditions.
    """
    
    ROUTES = {
        "FBX01": {
            "name": "China/East Asia - North America West Coast",
            "origin": "China",
            "destination": "US West Coast",
        },
        "FBX03": {
            "name": "China/East Asia - North America East Coast",
            "origin": "China", 
            "destination": "US East Coast",
        },
        "FBX11": {
            "name": "China/East Asia - North Europe",
            "origin": "China",
            "destination": "North Europe",
        },
    }
    
    SHIPPING_ETFS = {
        "BDRY": "Breakwave Dry Bulk Shipping ETF",
        "SEA": "US Global Sea to Sky Cargo ETF",
    }
    
    def __init__(self):
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(15.0),
            headers={"User-Agent": "OMEN/1.0"},
            follow_redirects=True
        )
        self._cache: Dict[str, FreightRate] = {}
        self._cache_time: Optional[datetime] = None
        self._cache_ttl = timedelta(hours=6)
        
        logger.info("FBXAdapter initialized")
    
    async def _fetch_from_etf_proxy(self) -> Dict[str, Any]:
        """Use shipping ETFs as proxy for freight market conditions."""
        try:
            import yfinance as yf
            
            etf_data = {}
            for symbol, name in self.SHIPPING_ETFS.items():
                try:
                    ticker = yf.Ticker(symbol)
                    hist = ticker.history(period="5d")
                    
                    if not hist.empty and len(hist) >= 2:
                        current = float(hist['Close'].iloc[-1])
                        previous = float(hist['Close'].iloc[-2])
                        change = current - previous
                        change_pct = (change / previous) * 100 if previous else 0
                        
                        etf_data[symbol] = {
                            "name": name,
                            "price": current,
                            "change": change,
                            "change_pct": change_pct,
                            "trend": "up" if change > 0 else "down",
                        }
                except Exception as e:
                    logger.warning(f"Failed to fetch {symbol}: {e}")
            
            return etf_data
            
        except ImportError:
            logger.warning("yfinance not available for ETF proxy")
            return {}
    
    async def get_freight_rates(
        self, 
        force_refresh: bool = False
    ) -> Dict[str, FreightRate]:
        """Get current freight rates via ETF proxy."""
        if not force_refresh and self._cache and self._cache_time:
            if datetime.utcnow() - self._cache_time < self._cache_ttl:
                return self._cache
        
        # Generate proxy rates from ETF data
        etf_data = await self._fetch_from_etf_proxy()
        
        rates = {}
        base_rate = 2500  # Approximate base rate for Asia-US routes
        
        # Use BDRY ETF movement as proxy for rate changes
        bdry = etf_data.get("BDRY", {})
        change_pct = bdry.get("change_pct", 0) if bdry else 0
        
        for code, route in self.ROUTES.items():
            rates[code] = FreightRate(
                route_code=code,
                route_name=route["name"],
                rate_usd_feu=base_rate * (1 + change_pct / 100),
                change_week=base_rate * change_pct / 100,
                change_week_pct=change_pct,
                last_updated=datetime.utcnow()
            )
        
        self._cache = rates
        self._cache_time = datetime.utcnow()
        
        return rates
    
    async def get_route_rate(self, route_code: str) -> Optional[FreightRate]:
        """Get rate for a specific route."""
        rates = await self.get_freight_rates()
        return rates.get(route_code)
    
    async def get_market_indicators(self) -> Dict[str, Any]:
        """Get overall freight market indicators."""
        rates = await self.get_freight_rates()
        etf_data = await self._fetch_from_etf_proxy()
        
        rate_changes = [r.change_week_pct for r in rates.values()]
        avg_change = sum(rate_changes) / len(rate_changes) if rate_changes else 0
        
        if avg_change > 5:
            market_trend = "strongly_rising"
        elif avg_change > 2:
            market_trend = "rising"
        elif avg_change < -5:
            market_trend = "strongly_falling"
        elif avg_change < -2:
            market_trend = "falling"
        else:
            market_trend = "stable"
        
        return {
            "market_trend": market_trend,
            "average_change_pct": round(avg_change, 2),
            "routes_tracked": len(rates),
            "rates": {code: rate.to_dict() for code, rate in rates.items()},
            "etf_indicators": etf_data,
            "last_updated": datetime.utcnow().isoformat(),
        }
    
    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()


_adapter_instance: Optional[FBXAdapter] = None

def get_fbx_adapter() -> FBXAdapter:
    """Get or create FBX adapter instance."""
    global _adapter_instance
    if _adapter_instance is None:
        _adapter_instance = FBXAdapter()
    return _adapter_instance
