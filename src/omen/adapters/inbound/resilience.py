"""
Resilience patterns for data source adapters.

Provides:
- Circuit breaker pattern
- Retry with exponential backoff
- Health check protocol
- Timeout handling

All data sources should use these patterns for production resilience.
"""

from __future__ import annotations

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from functools import wraps
from typing import Any, Callable, Generic, TypeVar, Protocol

from omen.infrastructure.resilience.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    create_source_circuit_breaker,
    get_circuit_breaker,
)

logger = logging.getLogger(__name__)

T = TypeVar("T")


class HealthCheckable(Protocol):
    """Protocol for health-checkable sources."""

    async def health_check(self) -> dict[str, Any]:
        """
        Check source health.

        Returns:
            Dict with keys:
            - healthy: bool
            - latency_ms: float
            - error: str | None
            - last_success: datetime | None
        """
        ...


class SourceHealth:
    """Track health status of a data source."""

    def __init__(self, source_name: str):
        self.source_name = source_name
        self.healthy = True
        self.last_success: datetime | None = None
        self.last_failure: datetime | None = None
        self.last_error: str | None = None
        self.consecutive_failures = 0
        self.total_requests = 0
        self.total_failures = 0
        self.total_latency_ms = 0.0

    def record_success(self, latency_ms: float) -> None:
        """Record a successful request."""
        self.healthy = True
        self.last_success = datetime.now(timezone.utc)
        self.consecutive_failures = 0
        self.total_requests += 1
        self.total_latency_ms += latency_ms

    def record_failure(self, error: str) -> None:
        """Record a failed request."""
        self.last_failure = datetime.now(timezone.utc)
        self.last_error = error
        self.consecutive_failures += 1
        self.total_requests += 1
        self.total_failures += 1

        # Mark unhealthy after 3 consecutive failures
        if self.consecutive_failures >= 3:
            self.healthy = False

    @property
    def avg_latency_ms(self) -> float:
        """Average latency in milliseconds."""
        successful = self.total_requests - self.total_failures
        if successful == 0:
            return 0.0
        return self.total_latency_ms / successful

    @property
    def failure_rate(self) -> float:
        """Failure rate as percentage."""
        if self.total_requests == 0:
            return 0.0
        return (self.total_failures / self.total_requests) * 100

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "source": self.source_name,
            "healthy": self.healthy,
            "last_success": self.last_success.isoformat() if self.last_success else None,
            "last_failure": self.last_failure.isoformat() if self.last_failure else None,
            "last_error": self.last_error,
            "consecutive_failures": self.consecutive_failures,
            "total_requests": self.total_requests,
            "total_failures": self.total_failures,
            "failure_rate_pct": round(self.failure_rate, 2),
            "avg_latency_ms": round(self.avg_latency_ms, 2),
        }


# Global health registry
_source_health: dict[str, SourceHealth] = {}


def get_source_health(source_name: str) -> SourceHealth:
    """Get or create health tracker for a source."""
    if source_name not in _source_health:
        _source_health[source_name] = SourceHealth(source_name)
    return _source_health[source_name]


def get_all_source_health() -> dict[str, dict[str, Any]]:
    """Get health status for all registered sources."""
    return {name: health.to_dict() for name, health in _source_health.items()}


def with_circuit_breaker(
    source_name: str,
    failure_threshold: int = 5,
    recovery_timeout: float = 30.0,
):
    """
    Decorator to add circuit breaker protection to a function.

    Args:
        source_name: Name of the source (for circuit identification)
        failure_threshold: Number of failures before opening circuit
        recovery_timeout: Seconds before attempting recovery
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        # Create circuit breaker for this source
        cb = create_source_circuit_breaker(
            source_name=source_name,
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
        )

        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            health = get_source_health(source_name)
            start_time = time.perf_counter()

            try:
                with cb:
                    result = func(*args, **kwargs)
                    latency_ms = (time.perf_counter() - start_time) * 1000
                    health.record_success(latency_ms)
                    return result
            except Exception as e:
                health.record_failure(str(e))
                raise

        @wraps(func)
        async def async_wrapper(*args, **kwargs) -> T:
            health = get_source_health(source_name)
            start_time = time.perf_counter()

            try:
                async with cb:
                    result = await func(*args, **kwargs)
                    latency_ms = (time.perf_counter() - start_time) * 1000
                    health.record_success(latency_ms)
                    return result
            except Exception as e:
                health.record_failure(str(e))
                raise

        # Return async or sync wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return wrapper

    return decorator


def with_retry(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    exponential_base: float = 2.0,
    retry_exceptions: tuple = (Exception,),
):
    """
    Decorator to add retry with exponential backoff.

    Args:
        max_attempts: Maximum number of attempts
        base_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds
        exponential_base: Base for exponential backoff
        retry_exceptions: Tuple of exceptions to retry on
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            last_exception = None

            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except retry_exceptions as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        delay = min(base_delay * (exponential_base**attempt), max_delay)
                        logger.warning(
                            f"Attempt {attempt + 1}/{max_attempts} failed: {e}. "
                            f"Retrying in {delay:.1f}s..."
                        )
                        time.sleep(delay)
                    else:
                        logger.error(f"All {max_attempts} attempts failed: {e}")

            raise last_exception

        @wraps(func)
        async def async_wrapper(*args, **kwargs) -> T:
            last_exception = None

            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except retry_exceptions as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        delay = min(base_delay * (exponential_base**attempt), max_delay)
                        logger.warning(
                            f"Attempt {attempt + 1}/{max_attempts} failed: {e}. "
                            f"Retrying in {delay:.1f}s..."
                        )
                        await asyncio.sleep(delay)
                    else:
                        logger.error(f"All {max_attempts} attempts failed: {e}")

            raise last_exception

        # Return async or sync wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return wrapper

    return decorator


class ResilientSourceBase(ABC):
    """
    Base class for resilient data sources.

    Provides:
    - Circuit breaker protection
    - Health tracking
    - Standardized health check interface
    """

    def __init__(self, source_name: str):
        self.source_name = source_name
        self._health = get_source_health(source_name)

        # Create circuit breaker for this source
        self._circuit_breaker = create_source_circuit_breaker(
            source_name=source_name,
            failure_threshold=5,
            recovery_timeout=30.0,
        )

    @property
    def health(self) -> SourceHealth:
        """Get health tracker for this source."""
        return self._health

    @property
    def is_healthy(self) -> bool:
        """Check if source is healthy."""
        return self._health.healthy

    @abstractmethod
    async def _do_health_check(self) -> bool:
        """
        Implement actual health check logic.

        Returns:
            True if healthy, False otherwise
        """
        pass

    async def health_check(self) -> dict[str, Any]:
        """
        Perform health check.

        Returns:
            Health status dictionary
        """
        start_time = time.perf_counter()

        try:
            healthy = await self._do_health_check()
            latency_ms = (time.perf_counter() - start_time) * 1000

            if healthy:
                self._health.record_success(latency_ms)
            else:
                self._health.record_failure("Health check returned unhealthy")

            return {
                "healthy": healthy,
                "latency_ms": round(latency_ms, 2),
                "error": None if healthy else "Health check failed",
                **self._health.to_dict(),
            }
        except Exception as e:
            latency_ms = (time.perf_counter() - start_time) * 1000
            self._health.record_failure(str(e))

            return {
                "healthy": False,
                "latency_ms": round(latency_ms, 2),
                "error": str(e),
                **self._health.to_dict(),
            }
