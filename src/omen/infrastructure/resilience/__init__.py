"""Resilience utilities: circuit breaker, bulkhead, retry, fallback."""

from omen.infrastructure.resilience.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerOpen,
    CircuitBreakerStats,
    CircuitState,
    get_circuit_breaker,
    register_circuit_breaker,
)
from omen.infrastructure.resilience.fallback_strategy import (
    CachedData,
    DataSourceWithFallback,
    FallbackCache,
    FallbackResponse,
    with_stale_fallback,
)

__all__ = [
    # Circuit Breaker
    "CircuitBreaker",
    "CircuitBreakerConfig",
    "CircuitBreakerOpen",
    "CircuitBreakerStats",
    "CircuitState",
    "get_circuit_breaker",
    "register_circuit_breaker",
    # Fallback Strategy
    "CachedData",
    "DataSourceWithFallback",
    "FallbackCache",
    "FallbackResponse",
    "with_stale_fallback",
]
