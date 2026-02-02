"""
OpenWeatherMap Real Implementation.

Fetches real weather alerts from OpenWeatherMap API.
Replaces mock data with actual API calls for production use.

API Documentation: https://openweathermap.org/api/one-call-3
"""

from __future__ import annotations

import logging
import os
import time
from datetime import datetime, timezone
from typing import Optional

import httpx
from pydantic import BaseModel, ConfigDict, Field

from omen.domain.models.raw_signal import RawSignalEvent
from omen.infrastructure.resilience.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    register_circuit_breaker,
)
from omen.application.ports.health_checkable import (
    HealthCheckable,
    HealthCheckResult,
    HealthStatus,
)

logger = logging.getLogger(__name__)


class OpenWeatherAlert(BaseModel):
    """Weather alert from OpenWeatherMap API."""

    model_config = ConfigDict(frozen=True)

    sender_name: str = Field(..., description="Alert source")
    event: str = Field(..., description="Alert event type")
    start: int = Field(..., description="Start timestamp (Unix)")
    end: int = Field(..., description="End timestamp (Unix)")
    description: str = Field(..., description="Alert description")
    tags: list[str] = Field(default_factory=list)


class OpenWeatherResponse(BaseModel):
    """OpenWeatherMap One Call API response."""

    model_config = ConfigDict(frozen=True)

    lat: float
    lon: float
    timezone: str
    alerts: list[OpenWeatherAlert] = Field(default_factory=list)


class OpenWeatherClient(HealthCheckable):
    """
    Real OpenWeatherMap API client.

    Fetches weather alerts for logistics-relevant locations.
    Uses circuit breaker for resilience.
    Implements HealthCheckable for centralized monitoring.

    Environment Variables:
        OPENWEATHER_API_KEY: API key for OpenWeatherMap
    """

    BASE_URL = "https://api.openweathermap.org/data/3.0"

    # Logistics-relevant coordinates for monitoring
    MONITORED_LOCATIONS: dict[str, dict[str, float]] = {
        # Major Asian ports
        "singapore": {"lat": 1.3521, "lon": 103.8198},
        "shanghai": {"lat": 31.2304, "lon": 121.4737},
        "hong_kong": {"lat": 22.3193, "lon": 114.1694},
        "shenzhen": {"lat": 22.5431, "lon": 114.0579},
        "busan": {"lat": 35.1796, "lon": 129.0756},
        "tokyo": {"lat": 35.6762, "lon": 139.6503},
        # European ports
        "rotterdam": {"lat": 51.9244, "lon": 4.4777},
        "antwerp": {"lat": 51.2194, "lon": 4.4025},
        "hamburg": {"lat": 53.5511, "lon": 9.9937},
        # American ports
        "los_angeles": {"lat": 33.9425, "lon": -118.4081},
        "long_beach": {"lat": 33.7701, "lon": -118.1937},
        "new_york": {"lat": 40.6892, "lon": -74.0445},
        # Vietnam ports (partner relevance)
        "ho_chi_minh": {"lat": 10.8231, "lon": 106.6297},
        "hai_phong": {"lat": 20.8449, "lon": 106.6881},
        "da_nang": {"lat": 16.0544, "lon": 108.2022},
        "cat_lai": {"lat": 10.7579, "lon": 106.7632},
        # Middle East (Suez/Red Sea)
        "port_said": {"lat": 31.2653, "lon": 32.3019},
        "jeddah": {"lat": 21.4858, "lon": 39.1925},
        "dubai": {"lat": 25.2048, "lon": 55.2708},
    }

    # Alert types relevant to logistics
    LOGISTICS_RELEVANT_EVENTS = {
        "tropical storm",
        "hurricane",
        "typhoon",
        "cyclone",
        "severe thunderstorm",
        "flood",
        "coastal flood",
        "high wind",
        "gale",
        "storm",
        "tsunami",
        "fog",
        "dense fog",
    }

    def __init__(
        self,
        api_key: Optional[str] = None,
        timeout: float = 30.0,
    ):
        self.api_key = api_key or os.getenv("OPENWEATHER_API_KEY")
        self._client = httpx.AsyncClient(timeout=timeout)
        self._circuit_breaker = CircuitBreaker(
            name="openweather",
            config=CircuitBreakerConfig(
                failure_threshold=5,
                timeout_seconds=60.0,
            ),
        )
        # Register for metrics
        register_circuit_breaker("openweather", self._circuit_breaker)

        if not self.api_key:
            logger.warning("OPENWEATHER_API_KEY not set. Weather alerts will be unavailable.")

    # ═══════════════════════════════════════════════════════════════════════════
    # HEALTH CHECKABLE IMPLEMENTATION
    # ═══════════════════════════════════════════════════════════════════════════

    @property
    def source_name(self) -> str:
        """Unique source name for health monitoring."""
        return "weather"

    @property
    def is_configured(self) -> bool:
        """Check if API key is configured."""
        return bool(self.api_key)

    async def fetch_all_alerts(self) -> list[RawSignalEvent]:
        """
        Fetch weather alerts for all monitored locations.

        Returns:
            List of RawSignalEvent for each alert
        """
        if not self.is_configured:
            logger.debug("OpenWeather not configured, returning empty alerts")
            return []

        events = []

        for location_name, coords in self.MONITORED_LOCATIONS.items():
            try:
                location_events = await self._fetch_location_alerts(location_name, coords)
                events.extend(location_events)
            except Exception as e:
                logger.warning("Failed to fetch alerts for %s: %s", location_name, e)

        logger.info(
            "OpenWeather: Fetched %d alerts from %d locations",
            len(events),
            len(self.MONITORED_LOCATIONS),
        )

        return events

    async def _fetch_location_alerts(
        self,
        location_name: str,
        coords: dict[str, float],
    ) -> list[RawSignalEvent]:
        """Fetch alerts for a specific location using circuit breaker."""
        from omen.infrastructure.resilience.circuit_breaker import CircuitBreakerOpen

        try:
            return await self._circuit_breaker.call(
                self._do_fetch_location_alerts,
                location_name,
                coords,
            )
        except CircuitBreakerOpen:
            logger.debug("Circuit breaker open for OpenWeather")
            return []
        except Exception as e:
            logger.error("OpenWeather fetch error for %s: %s", location_name, e)
            return []

    async def _do_fetch_location_alerts(
        self,
        location_name: str,
        coords: dict[str, float],
    ) -> list[RawSignalEvent]:
        """Actual fetch implementation (called through circuit breaker)."""
        response = await self._client.get(
            f"{self.BASE_URL}/onecall",
            params={
                "lat": coords["lat"],
                "lon": coords["lon"],
                "appid": self.api_key,
                "exclude": "minutely,hourly,daily,current",
            },
        )
        response.raise_for_status()

        data = response.json()

        events = []
        for alert_data in data.get("alerts", []):
            alert = OpenWeatherAlert(**alert_data)

            # Filter for logistics-relevant alerts
            if self._is_logistics_relevant(alert):
                event = self._alert_to_signal(location_name, coords, alert)
                events.append(event)

        return events

    def _is_logistics_relevant(self, alert: OpenWeatherAlert) -> bool:
        """Check if alert is relevant to logistics operations."""
        event_lower = alert.event.lower()

        for relevant in self.LOGISTICS_RELEVANT_EVENTS:
            if relevant in event_lower:
                return True

        # Check tags
        for tag in alert.tags:
            if tag.lower() in self.LOGISTICS_RELEVANT_EVENTS:
                return True

        return False

    def _alert_to_signal(
        self,
        location_name: str,
        coords: dict[str, float],
        alert: OpenWeatherAlert,
    ) -> RawSignalEvent:
        """Convert OpenWeatherMap alert to RawSignalEvent."""
        from omen.domain.models.raw_signal import MarketMetadata

        now = datetime.now(timezone.utc)
        start_dt = datetime.fromtimestamp(alert.start, tz=timezone.utc)
        end_dt = datetime.fromtimestamp(alert.end, tz=timezone.utc)

        # Calculate duration
        duration_hours = (end_dt - start_dt).total_seconds() / 3600

        # Determine probability based on alert type
        probability = self._calculate_probability(alert)

        # Generate event ID
        event_id = f"owm-{location_name}-{alert.event.replace(' ', '_')}-{alert.start}"

        return RawSignalEvent(
            event_id=event_id,
            title=f"Weather Alert: {alert.event} near {location_name.replace('_', ' ').title()}",
            description=alert.description[:500] if alert.description else None,
            probability=probability,
            probability_is_fallback=False,
            keywords=self._extract_keywords(alert, location_name),
            observed_at=now,
            market=MarketMetadata(
                source="openweather",
                market_id=f"weather-{location_name}",
                total_volume_usd=0.0,  # Weather alerts are not market-based
                current_liquidity_usd=0.0,
                created_at=start_dt,
                resolution_date=end_dt,
            ),
            source_metrics={
                "alert_type": alert.event,
                "sender": alert.sender_name,
                "duration_hours": round(duration_hours, 1),
                "start_time": start_dt.isoformat(),
                "end_time": end_dt.isoformat(),
                "location": location_name,
                "lat": coords["lat"],
                "lon": coords["lon"],
                "tags": alert.tags,
            },
        )

    def _calculate_probability(self, alert: OpenWeatherAlert) -> float:
        """
        Calculate probability based on alert type and severity.

        Weather alerts from official sources have high probability.
        """
        event_lower = alert.event.lower()

        # Severe events have very high probability of impact
        if any(s in event_lower for s in ["hurricane", "typhoon", "cyclone", "tsunami"]):
            return 0.95

        if any(s in event_lower for s in ["tropical storm", "severe", "flood"]):
            return 0.85

        if any(s in event_lower for s in ["storm", "gale", "high wind"]):
            return 0.75

        # Fog and other advisories
        return 0.65

    def _extract_keywords(
        self,
        alert: OpenWeatherAlert,
        location_name: str,
    ) -> list[str]:
        """Extract keywords for signal categorization."""
        keywords = [
            "weather",
            location_name.replace("_", " "),
            alert.event.lower(),
        ]

        # Add alert tags
        keywords.extend(tag.lower() for tag in alert.tags)

        # Add severity indicators
        event_lower = alert.event.lower()
        if "hurricane" in event_lower or "typhoon" in event_lower:
            keywords.extend(["tropical", "severe", "port closure"])
        if "flood" in event_lower:
            keywords.extend(["flood", "port disruption"])
        if "fog" in event_lower:
            keywords.extend(["visibility", "navigation hazard"])

        return list(set(keywords))

    async def health_check(self) -> HealthCheckResult:
        """
        Check OpenWeatherMap API health.

        Returns:
            HealthCheckResult with status and latency
        """
        if not self.is_configured:
            return HealthCheckResult.unknown(
                source_name=self.source_name,
                reason="OPENWEATHER_API_KEY not configured",
            )

        start_time = time.time()

        try:
            # Test with a single location (Singapore)
            response = await self._client.get(
                f"{self.BASE_URL}/onecall",
                params={
                    "lat": 1.3521,
                    "lon": 103.8198,
                    "appid": self.api_key,
                    "exclude": "minutely,hourly,daily,current,alerts",
                },
            )
            response.raise_for_status()

            latency_ms = (time.time() - start_time) * 1000

            # Check for slow response (degraded)
            if latency_ms > 5000:
                return HealthCheckResult.degraded(
                    source_name=self.source_name,
                    latency_ms=latency_ms,
                    reason=f"Slow response: {latency_ms:.0f}ms",
                    circuit_breaker_state=self._circuit_breaker.state.value,
                    monitored_locations=len(self.MONITORED_LOCATIONS),
                )

            return HealthCheckResult.healthy(
                source_name=self.source_name,
                latency_ms=latency_ms,
                circuit_breaker_state=self._circuit_breaker.state.value,
                monitored_locations=len(self.MONITORED_LOCATIONS),
            )

        except httpx.TimeoutException:
            return HealthCheckResult.unhealthy(
                source_name=self.source_name,
                error_message="Request timeout",
                latency_ms=(time.time() - start_time) * 1000,
            )
        except httpx.HTTPStatusError as e:
            return HealthCheckResult.unhealthy(
                source_name=self.source_name,
                error_message=f"HTTP {e.response.status_code}: {e.response.text[:100]}",
                latency_ms=(time.time() - start_time) * 1000,
            )
        except Exception as e:
            return HealthCheckResult.unhealthy(
                source_name=self.source_name,
                error_message=str(e),
                latency_ms=(time.time() - start_time) * 1000,
            )

    async def is_available(self) -> bool:
        """Quick check if weather source is available."""
        if not self.is_configured:
            return False
        result = await self.health_check()
        return result.status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED]

    async def close(self):
        """Close HTTP client."""
        await self._client.aclose()


# Factory function
def create_openweather_client(
    api_key: Optional[str] = None,
) -> OpenWeatherClient:
    """Create OpenWeatherMap client."""
    return OpenWeatherClient(api_key=api_key)
