"""
Aggregates health checks from all data sources.

Provides:
- Parallel health checking
- Caching to prevent excessive checks
- Overall system health calculation
- Individual source status
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel, Field

from omen.application.ports.health_checkable import (
    HealthCheckable,
    HealthCheckResult,
    HealthStatus,
)

logger = logging.getLogger(__name__)


class SourceHealthSummary(BaseModel):
    """Summary of all source health checks."""

    overall_status: HealthStatus = Field(..., description="Aggregate health status")
    total_sources: int = Field(..., description="Total number of registered sources")
    healthy_count: int = Field(0)
    degraded_count: int = Field(0)
    unhealthy_count: int = Field(0)
    unknown_count: int = Field(0)
    sources: dict[str, HealthCheckResult] = Field(default_factory=dict)
    checked_at: datetime = Field(default_factory=datetime.utcnow)
    cache_age_seconds: Optional[float] = Field(None, description="Age of cached data")


class SourceHealthAggregator:
    """
    Aggregates health status from all data sources.

    Features:
    - Parallel health checks for all sources
    - Caching to prevent excessive API calls
    - Overall status calculation
    - Per-source status tracking

    Usage:
        aggregator = SourceHealthAggregator([
            polymarket_client,
            weather_client,
            news_client,
        ])

        summary = await aggregator.check_all()
        print(f"Overall: {summary.overall_status}")
        print(f"Healthy: {summary.healthy_count}/{summary.total_sources}")
    """

    DEFAULT_CACHE_TTL = 30.0  # seconds
    DEFAULT_CHECK_TIMEOUT = 10.0  # seconds per source

    def __init__(
        self,
        sources: Optional[list[HealthCheckable]] = None,
        cache_ttl_seconds: float = DEFAULT_CACHE_TTL,
        check_timeout_seconds: float = DEFAULT_CHECK_TIMEOUT,
    ):
        self._sources: dict[str, HealthCheckable] = {}
        self._cache: dict[str, HealthCheckResult] = {}
        self._last_check: Optional[datetime] = None
        self._cache_ttl = cache_ttl_seconds
        self._check_timeout = check_timeout_seconds

        if sources:
            for source in sources:
                self.register_source(source)

    def register_source(self, source: HealthCheckable) -> None:
        """Register a source for health monitoring."""
        self._sources[source.source_name] = source
        logger.debug("Registered health check source: %s", source.source_name)

    def unregister_source(self, source_name: str) -> None:
        """Remove a source from monitoring."""
        self._sources.pop(source_name, None)
        self._cache.pop(source_name, None)

    @property
    def registered_sources(self) -> list[str]:
        """Get list of registered source names."""
        return list(self._sources.keys())

    async def check_all(self, force: bool = False) -> SourceHealthSummary:
        """
        Check health of all registered sources.

        Args:
            force: If True, bypass cache and check all sources

        Returns:
            SourceHealthSummary with overall and per-source status
        """
        # Check cache validity
        if not force and self._is_cache_valid():
            return self._build_summary(from_cache=True)

        # Run all health checks in parallel with timeout
        tasks = [
            self._check_source_with_timeout(name, source) for name, source in self._sources.items()
        ]

        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process results
            for result in results:
                if isinstance(result, HealthCheckResult):
                    self._cache[result.source_name] = result
                elif isinstance(result, Exception):
                    logger.error("Health check failed: %s", result)

        self._last_check = datetime.now(timezone.utc)

        return self._build_summary(from_cache=False)

    async def check_source(self, source_name: str) -> HealthCheckResult:
        """
        Check health of a specific source.

        Args:
            source_name: Name of the source to check

        Returns:
            HealthCheckResult for the source
        """
        source = self._sources.get(source_name)

        if not source:
            return HealthCheckResult.unknown(
                source_name=source_name,
                reason=f"Source '{source_name}' not registered",
            )

        result = await self._check_source_with_timeout(source_name, source)

        if isinstance(result, HealthCheckResult):
            self._cache[source_name] = result
            return result

        # Handle exception case
        return HealthCheckResult.unhealthy(
            source_name=source_name,
            error_message=str(result),
        )

    async def _check_source_with_timeout(
        self,
        name: str,
        source: HealthCheckable,
    ) -> HealthCheckResult:
        """Check single source with timeout protection."""
        try:
            return await asyncio.wait_for(
                source.health_check(),
                timeout=self._check_timeout,
            )
        except asyncio.TimeoutError:
            logger.warning("Health check timeout for source: %s", name)
            return HealthCheckResult.unhealthy(
                source_name=name,
                error_message=f"Health check timeout after {self._check_timeout}s",
            )
        except Exception as e:
            logger.error("Health check error for %s: %s", name, e)
            return HealthCheckResult.unhealthy(
                source_name=name,
                error_message=str(e),
            )

    def _is_cache_valid(self) -> bool:
        """Check if cached results are still valid."""
        if not self._last_check:
            return False

        elapsed = (datetime.now(timezone.utc) - self._last_check).total_seconds()
        return elapsed < self._cache_ttl

    def _build_summary(self, from_cache: bool = False) -> SourceHealthSummary:
        """Build summary from cached results."""
        healthy = 0
        degraded = 0
        unhealthy = 0
        unknown = 0

        for result in self._cache.values():
            if result.status == HealthStatus.HEALTHY:
                healthy += 1
            elif result.status == HealthStatus.DEGRADED:
                degraded += 1
            elif result.status == HealthStatus.UNHEALTHY:
                unhealthy += 1
            else:
                unknown += 1

        # Calculate overall status
        total = len(self._sources)

        if total == 0:
            overall = HealthStatus.UNKNOWN
        elif unhealthy == 0 and degraded == 0 and unknown == 0:
            overall = HealthStatus.HEALTHY
        elif unhealthy == 0 and unknown == 0:
            overall = HealthStatus.DEGRADED
        elif healthy > unhealthy:
            overall = HealthStatus.DEGRADED
        else:
            overall = HealthStatus.UNHEALTHY

        # Calculate cache age
        cache_age = None
        if self._last_check:
            cache_age = (datetime.now(timezone.utc) - self._last_check).total_seconds()

        return SourceHealthSummary(
            overall_status=overall,
            total_sources=total,
            healthy_count=healthy,
            degraded_count=degraded,
            unhealthy_count=unhealthy,
            unknown_count=unknown,
            sources=self._cache.copy(),
            checked_at=self._last_check or datetime.now(timezone.utc),
            cache_age_seconds=cache_age,
        )

    def get_cached_result(self, source_name: str) -> Optional[HealthCheckResult]:
        """Get cached result for a source without triggering check."""
        return self._cache.get(source_name)

    def clear_cache(self) -> None:
        """Clear all cached results."""
        self._cache.clear()
        self._last_check = None


# ═══════════════════════════════════════════════════════════════════════════════
# GLOBAL INSTANCE
# ═══════════════════════════════════════════════════════════════════════════════

_health_aggregator: Optional[SourceHealthAggregator] = None


def get_health_aggregator() -> SourceHealthAggregator:
    """Get or create the global health aggregator."""
    global _health_aggregator
    if _health_aggregator is None:
        _health_aggregator = SourceHealthAggregator()
    return _health_aggregator


def register_health_check_source(source: HealthCheckable) -> None:
    """Register a source with the global health aggregator."""
    aggregator = get_health_aggregator()
    aggregator.register_source(source)
