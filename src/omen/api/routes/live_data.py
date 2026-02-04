"""
Live Data Aggregation Endpoints

Fetches real data from all configured sources and generates live signals.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List
import random
import hashlib

from fastapi import APIRouter, Depends, HTTPException, Query

from omen.domain.models.omen_signal import (
    OmenSignal, 
    ConfidenceLevel, 
    SignalCategory,
    EvidenceItem,
    GeographicContext,
    TemporalContext,
)
from omen.api.dependencies import get_repository
from omen.application.ports.signal_repository import SignalRepository
from omen.api.route_dependencies import require_signals_read
from omen.infrastructure.security.unified_auth import AuthContext
from omen.infrastructure.security.redaction import redact_for_api
from omen.infrastructure.activity.activity_logger import get_activity_logger

logger = logging.getLogger(__name__)
router = APIRouter()


def _generate_signal_id() -> str:
    """Generate a unique LIVE signal ID."""
    timestamp = datetime.now(timezone.utc).timestamp()
    random_part = random.randint(1000, 9999)
    hash_input = f"{timestamp}-{random_part}"
    hash_hex = hashlib.md5(hash_input.encode()).hexdigest()[:8].upper()
    return f"OMEN-LIVE{hash_hex}"


async def _fetch_weather_signals() -> List[Dict[str, Any]]:
    """Fetch weather data and convert to signal format."""
    try:
        from omen.adapters.inbound.weather.openmeteo_adapter import get_openmeteo_adapter
        
        adapter = get_openmeteo_adapter()
        signals = []
        
        # Get weather for major ports
        for port_key in ["singapore", "shanghai", "ho_chi_minh", "rotterdam"]:
            try:
                weather = await adapter.get_port_weather(port_key)
                
                if weather.is_severe:
                    signals.append({
                        "title": f"Severe Weather Alert: {weather.location}",
                        "description": f"{weather.weather_description} with {weather.wind_speed_kmh:.0f} km/h winds. Temperature: {weather.temperature_c:.1f}°C.",
                        "probability": 0.85 if weather.weather_code >= 95 else 0.70,
                        "category": SignalCategory.WEATHER,
                        "confidence": 0.80,
                        "source": "openmeteo",
                        "source_url": f"https://open-meteo.com",
                        "regions": [port_key],
                    })
                elif weather.wind_speed_kmh > 30:
                    signals.append({
                        "title": f"High Winds at {weather.location}",
                        "description": f"Wind speed {weather.wind_speed_kmh:.0f} km/h may affect port operations.",
                        "probability": 0.60,
                        "category": SignalCategory.WEATHER,
                        "confidence": 0.75,
                        "source": "openmeteo",
                        "source_url": f"https://open-meteo.com",
                        "regions": [port_key],
                    })
            except Exception as e:
                logger.debug(f"Failed to get weather for {port_key}: {e}")
                
        return signals
    except ImportError:
        logger.warning("Weather adapter not available")
        return []
    except Exception as e:
        logger.warning(f"Weather fetch failed: {e}")
        return []


async def _fetch_news_signals() -> List[Dict[str, Any]]:
    """Fetch news and convert to signal format."""
    try:
        from omen.adapters.inbound.news.newsdata_adapter import get_newsdata_adapter
        
        adapter = get_newsdata_adapter()
        signals = []
        
        # Get logistics-related news
        articles = await adapter.get_logistics_news(size=10)
        
        for article in articles[:5]:  # Limit to 5 signals
            # Determine category based on content
            title_lower = article.title.lower()
            if any(kw in title_lower for kw in ["tariff", "sanction", "regulation", "policy"]):
                category = SignalCategory.REGULATORY
            elif any(kw in title_lower for kw in ["war", "conflict", "military", "attack"]):
                category = SignalCategory.GEOPOLITICAL
            elif any(kw in title_lower for kw in ["price", "cost", "market", "stock"]):
                category = SignalCategory.ECONOMIC
            else:
                category = SignalCategory.OTHER
            
            # Calculate confidence based on sentiment
            base_conf = 0.65
            if article.sentiment == "positive":
                base_conf = 0.70
            elif article.sentiment == "negative":
                base_conf = 0.75  # Negative news often more impactful
            
            signals.append({
                "title": article.title[:200],
                "description": (article.description or "")[:500],
                "probability": 0.5 + (article.sentiment_score * 0.2),
                "category": category,
                "confidence": base_conf,
                "source": "newsdata",
                "source_url": article.link,
                "regions": article.country if article.country else [],
            })
        
        return signals
    except ImportError:
        logger.warning("News adapter not available")
        return []
    except Exception as e:
        logger.warning(f"News fetch failed: {e}")
        return []


async def _fetch_freight_signals() -> List[Dict[str, Any]]:
    """Fetch freight data and convert to signal format."""
    try:
        from omen.adapters.inbound.freight.fbx_adapter import get_fbx_adapter
        
        adapter = get_fbx_adapter()
        signals = []
        
        indicators = await adapter.get_market_indicators()
        
        trend = indicators.get("market_trend", "stable")
        change_pct = indicators.get("average_change_pct", 0)
        
        if abs(change_pct) > 3:
            direction = "rising" if change_pct > 0 else "falling"
            signals.append({
                "title": f"Freight Rates {direction.title()} - {abs(change_pct):.1f}% Change",
                "description": f"Container freight rates are {direction}. Market trend: {trend}. This may impact shipping costs.",
                "probability": 0.75 if abs(change_pct) > 5 else 0.60,
                "category": SignalCategory.ECONOMIC,
                "confidence": 0.70,
                "source": "fbx",
                "source_url": "https://fbx.freightos.com",
                "regions": ["global"],
            })
        
        # Add individual route signals if significant change
        for code, rate in indicators.get("rates", {}).items():
            if isinstance(rate, dict) and abs(rate.get("change_week_pct", 0)) > 5:
                signals.append({
                    "title": f"{rate.get('route_name', code)}: {rate.get('trend', 'changing').title()} Rates",
                    "description": f"Freight rate ${rate.get('rate_usd_feu', 0):.0f}/FEU, {rate.get('change_week_pct', 0):+.1f}% weekly change.",
                    "probability": 0.65,
                    "category": SignalCategory.ECONOMIC,
                    "confidence": 0.72,
                    "source": "fbx",
                    "source_url": "https://fbx.freightos.com",
                    "regions": ["asia", "us"],
                })
        
        return signals
    except ImportError:
        logger.warning("Freight adapter not available")
        return []
    except Exception as e:
        logger.warning(f"Freight fetch failed: {e}")
        return []


def _create_omen_signal(raw: Dict[str, Any]) -> OmenSignal:
    """Convert raw signal data to OmenSignal."""
    now = datetime.now(timezone.utc)
    
    confidence_score = raw.get("confidence", 0.65)
    if confidence_score >= 0.7:
        confidence_level = ConfidenceLevel.HIGH
    elif confidence_score >= 0.4:
        confidence_level = ConfidenceLevel.MEDIUM
    else:
        confidence_level = ConfidenceLevel.LOW
    
    return OmenSignal(
        signal_id=_generate_signal_id(),
        source_event_id=f"live-{raw.get('source', 'unknown')}-{now.timestamp()}",
        title=raw.get("title", "Unknown Signal"),
        description=raw.get("description", ""),
        probability=raw.get("probability", 0.5),
        probability_source=raw.get("source", "live"),
        confidence_score=confidence_score,
        confidence_level=confidence_level,
        category=raw.get("category", SignalCategory.OTHER),
        tags=raw.get("regions", []),
        geographic=GeographicContext(
            regions=raw.get("regions", []),
            chokepoints=[],
        ),
        temporal=TemporalContext(
            event_horizon=None,
            resolution_date=None,
        ),
        evidence=[
            EvidenceItem(
                source=raw.get("source", "live"),
                source_type="api",
                url=raw.get("source_url", ""),
            )
        ],
        trace_id=f"live-{now.strftime('%Y%m%d%H%M%S')}",
        ruleset_version="1.0.0",
        source_url=raw.get("source_url", ""),
        observed_at=now,
        generated_at=now,
    )


@router.post(
    "/generate",
    summary="Generate live signals from all sources",
    description="Fetches real data from weather, news, and freight sources and generates live signals.",
)
async def generate_live_signals(
    repository: SignalRepository = Depends(get_repository),
    auth: AuthContext = Depends(require_signals_read),  # RBAC: read:signals
) -> dict:
    """
    Generate live signals from all available data sources.
    """
    activity = get_activity_logger()
    
    # Fetch data from all sources in parallel
    results = await asyncio.gather(
        _fetch_weather_signals(),
        _fetch_news_signals(),
        _fetch_freight_signals(),
        return_exceptions=True,
    )
    
    all_raw_signals = []
    sources_status = {}
    
    source_names = ["weather", "news", "freight"]
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            sources_status[source_names[i]] = {"status": "error", "error": str(result), "count": 0}
            logger.warning(f"Source {source_names[i]} failed: {result}")
        elif isinstance(result, list):
            all_raw_signals.extend(result)
            sources_status[source_names[i]] = {"status": "ok", "count": len(result)}
    
    # Convert to OmenSignals and save
    created_signals = []
    for raw in all_raw_signals:
        try:
            signal = _create_omen_signal(raw)
            repository.save(signal)
            created_signals.append(signal)
            
            activity.log_signal_generated(
                signal_id=signal.signal_id,
                title=signal.title,
                confidence_label=signal.confidence_level.value,
                confidence_level=str(signal.confidence_score),
            )
        except Exception as e:
            logger.warning(f"Failed to create signal: {e}")
    
    activity.log_system_event(
        f"Live signal generation: {len(created_signals)} signals from {len([s for s in sources_status.values() if s.get('status') == 'ok'])} sources"
    )
    
    return {
        "success": True,
        "signals_created": len(created_signals),
        "sources": sources_status,
        "signal_ids": [s.signal_id for s in created_signals],
    }


@router.get(
    "/signals",
    summary="Get live signals only",
    description="Returns only live signals (no demo signals).",
)
async def get_live_signals(
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
    repository: SignalRepository = Depends(get_repository),
    auth: AuthContext = Depends(require_signals_read),  # RBAC: read:signals
) -> dict:
    """
    Get live signals only (excludes demo signals).
    """
    # Get all recent signals and filter
    signals = repository.find_recent(limit=limit * 2, offset=0)
    
    # Filter out demo signals
    live_signals = [s for s in signals if "DEMO" not in s.signal_id]
    
    # Apply pagination
    paginated = live_signals[offset:offset + limit]
    
    return {
        "signals": [redact_for_api(s) for s in paginated],
        "total": len(live_signals),
        "limit": limit,
        "offset": offset,
        "data_mode": "live",
    }


@router.get(
    "/status",
    summary="Get live data source status",
    description="Check which live data sources are available and working.",
)
async def get_live_data_status(
    auth: AuthContext = Depends(require_signals_read),  # RBAC: read:signals
) -> dict:
    """
    Check status of all live data sources.
    """
    sources = {}
    
    # Check weather
    try:
        from omen.adapters.inbound.weather.openmeteo_adapter import get_openmeteo_adapter
        adapter = get_openmeteo_adapter()
        weather = await adapter.get_port_weather("singapore")
        sources["weather"] = {
            "status": "available",
            "provider": "openmeteo",
            "sample": f"{weather.location}: {weather.temperature_c:.1f}°C",
        }
    except Exception as e:
        sources["weather"] = {"status": "error", "error": str(e)}
    
    # Check news
    try:
        from omen.adapters.inbound.news.newsdata_adapter import get_newsdata_adapter
        adapter = get_newsdata_adapter()
        articles = await adapter.get_latest_news(size=1)
        sources["news"] = {
            "status": "available",
            "provider": "newsdata",
            "sample": articles[0].title[:50] + "..." if articles else "No articles",
        }
    except Exception as e:
        sources["news"] = {"status": "error", "error": str(e)}
    
    # Check freight
    try:
        from omen.adapters.inbound.freight.fbx_adapter import get_fbx_adapter
        adapter = get_fbx_adapter()
        indicators = await adapter.get_market_indicators()
        sources["freight"] = {
            "status": "available",
            "provider": "fbx",
            "sample": f"Market trend: {indicators.get('market_trend', 'unknown')}",
        }
    except Exception as e:
        sources["freight"] = {"status": "error", "error": str(e)}
    
    available_count = sum(1 for s in sources.values() if s.get("status") == "available")
    
    return {
        "sources": sources,
        "available_count": available_count,
        "total_count": len(sources),
        "ready": available_count > 0,
    }
