"""
Circuit Breaker Pattern Implementation

States:
- CLOSED: Normal operation, requests pass through
- OPEN: Failing, requests are rejected immediately
- HALF_OPEN: Testing if service recovered

Transitions:
- CLOSED -> OPEN: When failure threshold exceeded
- OPEN -> HALF_OPEN: After timeout period
- HALF_OPEN -> CLOSED: When test requests succeed
- HALF_OPEN -> OPEN: When test request fails
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Awaitable, Callable, TypeVar

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker behavior."""

    failure_threshold: int = 5
    success_threshold: int = 3
    timeout_seconds: float = 30.0
    half_open_max_calls: int = 3
    window_size_seconds: float = 60.0
    failure_rate_threshold: float = 0.5
    min_calls_in_window: int = 10


@dataclass
class CircuitBreakerStats:
    """Statistics for monitoring and debugging."""

    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    consecutive_failures: int = 0
    consecutive_successes: int = 0
    last_failure_time: datetime | None = None
    last_success_time: datetime | None = None
    last_state_change: datetime = field(default_factory=datetime.utcnow)
    total_calls: int = 0
    total_failures: int = 0
    total_successes: int = 0
    total_rejected: int = 0


class CircuitBreakerOpen(Exception):
    """Raised when circuit is open and request is rejected."""

    def __init__(self, circuit_name: str, retry_after: float):
        self.circuit_name = circuit_name
        self.retry_after = retry_after
        super().__init__(
            f"Circuit '{circuit_name}' is OPEN. Retry after {retry_after:.1f}s"
        )


T = TypeVar("T")

# Registry for metrics: name -> CircuitBreaker
_circuit_breakers: dict[str, "CircuitBreaker[Any]"] = {}


def register_circuit_breaker(name: str, cb: "CircuitBreaker[Any]") -> None:
    """Register a circuit breaker for metrics/API exposure."""
    _circuit_breakers[name] = cb


def get_circuit_breaker(name: str) -> "CircuitBreaker[Any] | None":
    """Get a registered circuit breaker by name."""
    return _circuit_breakers.get(name)


def create_source_circuit_breaker(
    source_name: str,
    failure_threshold: int = 5,
    recovery_timeout: float = 30.0,
) -> "CircuitBreaker[Any]":
    """
    Create and register a circuit breaker for a data source.
    
    Args:
        source_name: Name of the source (used for registration and metrics)
        failure_threshold: Number of failures before opening circuit
        recovery_timeout: Seconds before attempting recovery
    
    Returns:
        Configured CircuitBreaker instance
    """
    # Check if already registered
    existing = get_circuit_breaker(source_name)
    if existing is not None:
        return existing
    
    config = CircuitBreakerConfig(
        failure_threshold=failure_threshold,
        timeout_seconds=recovery_timeout,
        success_threshold=2,  # Quick recovery for sources
    )
    
    cb = CircuitBreaker(name=source_name, config=config)
    register_circuit_breaker(source_name, cb)
    
    return cb


class CircuitBreaker:
    """
    Circuit Breaker with failure threshold, sliding-window failure rate,
    half-open probing, and async support.
    """

    def __init__(
        self,
        name: str,
        config: CircuitBreakerConfig | None = None,
        on_state_change: Callable[[CircuitState, CircuitState], None] | None = None,
    ):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.on_state_change = on_state_change

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._consecutive_failures = 0
        self._consecutive_successes = 0
        self._last_failure_time: datetime | None = None
        self._opened_at: datetime | None = None
        self._half_open_calls = 0
        self._last_success_time: datetime | None = None
        self._lock = asyncio.Lock()

        self._call_results: list[tuple[datetime, bool]] = []
        self._stats = CircuitBreakerStats()

    @property
    def state(self) -> CircuitState:
        return self._state

    @property
    def stats(self) -> CircuitBreakerStats:
        """Return current statistics (snapshot)."""
        self._stats.state = self._state
        self._stats.failure_count = self._failure_count
        self._stats.success_count = self._success_count
        self._stats.consecutive_failures = self._consecutive_failures
        self._stats.consecutive_successes = self._consecutive_successes
        self._stats.last_failure_time = self._last_failure_time
        self._stats.last_success_time = self._last_success_time
        return self._stats

    async def call(
        self,
        func: Callable[..., Awaitable[T]],
        *args: Any,
        **kwargs: Any,
    ) -> T:
        """
        Execute async function through the circuit breaker.

        Raises:
            CircuitBreakerOpen: If circuit is open.
        """
        async with self._lock:
            self._stats.total_calls += 1
            await self._check_state_transition()

            if self._state == CircuitState.OPEN:
                self._stats.total_rejected += 1
                retry_after = self._get_retry_after()
                raise CircuitBreakerOpen(self.name, retry_after)

            if self._state == CircuitState.HALF_OPEN:
                if self._half_open_calls >= self.config.half_open_max_calls:
                    self._stats.total_rejected += 1
                    raise CircuitBreakerOpen(self.name, 1.0)
                self._half_open_calls += 1

        try:
            result = await func(*args, **kwargs)
            await self._record_success()
            return result
        except Exception as e:
            await self._record_failure(e)
            raise

    async def _check_state_transition(self) -> None:
        now = datetime.now(timezone.utc)

        if self._state == CircuitState.OPEN:
            if self._opened_at:
                elapsed = (now - self._opened_at).total_seconds()
                if elapsed >= self.config.timeout_seconds:
                    await self._transition_to(CircuitState.HALF_OPEN)

        elif self._state == CircuitState.CLOSED:
            self._clean_old_results()
            if len(self._call_results) >= self.config.min_calls_in_window:
                failure_rate = self._calculate_failure_rate()
                if failure_rate >= self.config.failure_rate_threshold:
                    logger.warning(
                        "Circuit '%s' failure rate %.1f%% exceeds threshold %.1f%%",
                        self.name,
                        failure_rate * 100,
                        self.config.failure_rate_threshold * 100,
                    )
                    await self._transition_to(CircuitState.OPEN)

    async def _record_success(self) -> None:
        async with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                self._half_open_calls -= 1
            self._success_count += 1
            self._consecutive_successes += 1
            self._consecutive_failures = 0
            self._stats.total_successes += 1
            self._stats.last_success_time = datetime.now(timezone.utc)
            self._call_results.append((datetime.now(timezone.utc), True))

            self._last_success_time = datetime.now(timezone.utc)
            if self._state == CircuitState.HALF_OPEN:
                if self._consecutive_successes >= self.config.success_threshold:
                    await self._transition_to(CircuitState.CLOSED)

    async def _record_failure(self, error: Exception) -> None:
        async with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                self._half_open_calls -= 1
            self._failure_count += 1
            self._consecutive_failures += 1
            self._consecutive_successes = 0
            self._stats.total_failures += 1
            self._stats.last_failure_time = datetime.now(timezone.utc)
            self._last_failure_time = datetime.now(timezone.utc)
            self._call_results.append((datetime.now(timezone.utc), False))

            logger.warning(
                "Circuit '%s' recorded failure #%s: %s",
                self.name,
                self._consecutive_failures,
                error,
            )

            if self._state == CircuitState.HALF_OPEN:
                await self._transition_to(CircuitState.OPEN)
            elif self._state == CircuitState.CLOSED:
                if self._consecutive_failures >= self.config.failure_threshold:
                    logger.warning(
                        "Circuit '%s' hit %s consecutive failures, opening",
                        self.name,
                        self._consecutive_failures,
                    )
                    await self._transition_to(CircuitState.OPEN)

    async def _transition_to(self, new_state: CircuitState) -> None:
        old_state = self._state
        self._state = new_state
        self._stats.last_state_change = datetime.now(timezone.utc)

        logger.info(
            "Circuit '%s' state transition: %s -> %s",
            self.name,
            old_state.value,
            new_state.value,
        )

        if new_state == CircuitState.OPEN:
            self._opened_at = datetime.now(timezone.utc)
        elif new_state == CircuitState.HALF_OPEN:
            self._half_open_calls = 0
            self._consecutive_successes = 0
        elif new_state == CircuitState.CLOSED:
            self._consecutive_failures = 0
            self._consecutive_successes = 0
            self._opened_at = None

        if self.on_state_change:
            try:
                self.on_state_change(old_state, new_state)
            except Exception as e:
                logger.error("Error in circuit state change callback: %s", e)

    def _get_retry_after(self) -> float:
        if self._opened_at:
            elapsed = (datetime.now(timezone.utc) - self._opened_at).total_seconds()
            return max(0.0, self.config.timeout_seconds - elapsed)
        return self.config.timeout_seconds

    def _clean_old_results(self) -> None:
        cutoff = datetime.now(timezone.utc) - timedelta(
            seconds=self.config.window_size_seconds
        )
        self._call_results = [(t, s) for t, s in self._call_results if t > cutoff]

    def _calculate_failure_rate(self) -> float:
        if not self._call_results:
            return 0.0
        failures = sum(1 for _, success in self._call_results if not success)
        return failures / len(self._call_results)

    async def reset(self) -> None:
        """Manually reset circuit to CLOSED (e.g. after confirming service is healthy)."""
        async with self._lock:
            logger.info("Circuit '%s' manually reset", self.name)
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            self._success_count = 0
            self._consecutive_failures = 0
            self._consecutive_successes = 0
            self._opened_at = None
            self._half_open_calls = 0
            self._call_results.clear()
