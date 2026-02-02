"""
Fallback Strategy for Data Sources.

Implements a graceful degradation pattern:
1. Try live data first
2. On failure, return cached (stale) data with warning
3. If no cache, return degraded response with clear indicator

This is better than mock data because:
- Stale real data is more valuable than fake data
- Consumers can see data freshness and make informed decisions
- No silent failures - always transparent about data quality
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Generic, Optional, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


@dataclass
class CachedData(Generic[T]):
    """Cached data with metadata."""

    data: T
    cached_at: datetime
    source: str
    ttl_seconds: int = 3600  # 1 hour default

    @property
    def age_seconds(self) -> float:
        """Age of cached data in seconds."""
        now = datetime.now(timezone.utc)
        if self.cached_at.tzinfo is None:
            cached = self.cached_at.replace(tzinfo=timezone.utc)
        else:
            cached = self.cached_at
        return (now - cached).total_seconds()

    @property
    def is_expired(self) -> bool:
        """Check if cache has expired."""
        return self.age_seconds > self.ttl_seconds

    @property
    def is_stale(self) -> bool:
        """Check if data is stale (older than 5 minutes)."""
        return self.age_seconds > 300

    @property
    def freshness_level(self) -> str:
        """Get freshness level for transparency."""
        age = self.age_seconds
        if age < 60:
            return "fresh"
        elif age < 300:
            return "recent"
        elif age < 3600:
            return "stale"
        elif age < 86400:
            return "old"
        else:
            return "very_old"


@dataclass
class FallbackResponse(Generic[T]):
    """Response with fallback metadata."""

    data: T
    source: str
    is_fallback: bool = False
    fallback_reason: Optional[str] = None
    data_freshness: str = "live"
    data_age_seconds: Optional[float] = None
    warning: Optional[str] = None

    def to_headers(self) -> dict[str, str]:
        """Convert to HTTP headers for transparency."""
        headers = {
            "X-OMEN-Data-Source": self.source,
            "X-OMEN-Data-Freshness": self.data_freshness,
        }
        if self.is_fallback:
            headers["X-OMEN-Fallback"] = "true"
            headers["X-OMEN-Fallback-Reason"] = self.fallback_reason or "unknown"
        if self.data_age_seconds is not None:
            headers["X-OMEN-Data-Age-Seconds"] = str(int(self.data_age_seconds))
        if self.warning:
            headers["X-OMEN-Warning"] = self.warning
        return headers


class FallbackCache(Generic[T]):
    """
    In-memory cache for fallback data.

    Stores recent successful responses to use as fallback
    when live data sources fail.
    """

    def __init__(self, ttl_seconds: int = 3600):
        self._cache: dict[str, CachedData[T]] = {}
        self._ttl = ttl_seconds

    def get(self, key: str) -> Optional[CachedData[T]]:
        """Get cached data if available and not expired."""
        cached = self._cache.get(key)
        if cached and not cached.is_expired:
            return cached
        return None

    def get_stale(self, key: str) -> Optional[CachedData[T]]:
        """Get cached data even if expired (for fallback)."""
        return self._cache.get(key)

    def set(self, key: str, data: T, source: str) -> None:
        """Cache data with current timestamp."""
        self._cache[key] = CachedData(
            data=data,
            cached_at=datetime.now(timezone.utc),
            source=source,
            ttl_seconds=self._ttl,
        )

    def clear(self, key: Optional[str] = None) -> None:
        """Clear cache (all or specific key)."""
        if key:
            self._cache.pop(key, None)
        else:
            self._cache.clear()

    def stats(self) -> dict[str, object]:
        """Get cache statistics."""
        entries: list[dict[str, object]] = []
        for key, cached in self._cache.items():
            entries.append(
                {
                    "key": key,
                    "source": cached.source,
                    "age_seconds": cached.age_seconds,
                    "freshness": cached.freshness_level,
                    "is_expired": cached.is_expired,
                }
            )
        return {
            "total_entries": len(self._cache),
            "ttl_seconds": self._ttl,
            "entries": entries,
        }


class DataSourceWithFallback(Generic[T]):
    """
    Wrapper that adds fallback capability to any data source.

    Usage:
        source = DataSourceWithFallback(
            name="polymarket",
            fetch_fn=lambda: polymarket_client.get_events(),
            cache_ttl=3600,
        )

        result = source.fetch("events")
        if result.is_fallback:
            logger.warning(f"Using fallback: {result.warning}")
    """

    def __init__(
        self,
        name: str,
        fetch_fn: Callable[[], T],
        cache_ttl: int = 3600,
    ):
        self.name = name
        self._fetch_fn = fetch_fn
        self._cache = FallbackCache[T](ttl_seconds=cache_ttl)

    def fetch(self, cache_key: str) -> FallbackResponse[T]:
        """
        Fetch data with automatic fallback.

        1. Try live fetch
        2. On success, cache and return
        3. On failure, try stale cache
        4. If no cache, raise exception
        """
        try:
            # Try live fetch
            data = self._fetch_fn()

            # Cache successful result
            self._cache.set(cache_key, data, self.name)

            return FallbackResponse(
                data=data,
                source=self.name,
                is_fallback=False,
                data_freshness="live",
            )

        except Exception as e:
            logger.warning("Live fetch failed for %s: %s. Attempting fallback.", self.name, e)

            # Try stale cache
            cached = self._cache.get_stale(cache_key)

            if cached:
                logger.info(
                    "Using stale cache for %s (age: %ds, freshness: %s)",
                    self.name,
                    int(cached.age_seconds),
                    cached.freshness_level,
                )

                return FallbackResponse(
                    data=cached.data,
                    source=self.name,
                    is_fallback=True,
                    fallback_reason=str(e),
                    data_freshness=cached.freshness_level,
                    data_age_seconds=cached.age_seconds,
                    warning=f"Using stale data from {cached.freshness_level} cache. "
                    f"Live fetch failed: {str(e)[:100]}",
                )

            # No cache available - re-raise with context
            raise RuntimeError(
                f"Data source {self.name} failed and no cached data available. "
                f"Original error: {e}"
            ) from e

    def invalidate_cache(self, cache_key: Optional[str] = None) -> None:
        """Invalidate cached data."""
        self._cache.clear(cache_key)

    def cache_stats(self) -> dict:
        """Get cache statistics."""
        return self._cache.stats()


# ═══════════════════════════════════════════════════════════════════════════════
# DECORATOR FOR EASY INTEGRATION
# ═══════════════════════════════════════════════════════════════════════════════


def with_stale_fallback(
    cache_key: str,
    cache_ttl: int = 3600,
    source_name: str = "unknown",
):
    """
    Decorator to add stale-data fallback to any function.

    Usage:
        @with_stale_fallback(cache_key="polymarket_events", cache_ttl=3600)
        def fetch_polymarket_events():
            return client.get_events()
    """
    _cache: dict[str, CachedData] = {}

    def decorator(fn: Callable[[], T]) -> Callable[[], FallbackResponse[T]]:
        def wrapper() -> FallbackResponse[T]:
            nonlocal _cache

            try:
                data = fn()
                _cache[cache_key] = CachedData(
                    data=data,
                    cached_at=datetime.now(timezone.utc),
                    source=source_name,
                    ttl_seconds=cache_ttl,
                )
                return FallbackResponse(
                    data=data,
                    source=source_name,
                    is_fallback=False,
                    data_freshness="live",
                )
            except Exception as e:
                cached = _cache.get(cache_key)
                if cached:
                    return FallbackResponse(
                        data=cached.data,
                        source=source_name,
                        is_fallback=True,
                        fallback_reason=str(e),
                        data_freshness=cached.freshness_level,
                        data_age_seconds=cached.age_seconds,
                        warning=f"Using cached data ({cached.freshness_level}). Error: {str(e)[:100]}",
                    )
                raise

        return wrapper

    return decorator
