"""
Retry and Circuit Breaker utilities.

Uses tenacity for retry logic with exponential backoff.
"""

import logging
from datetime import datetime, timedelta
from enum import Enum
from functools import wraps
from threading import Lock
from typing import Callable, ParamSpec, TypeVar

from tenacity import (
    RetryError,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
    before_sleep_log,
)

from omen.domain.errors import (
    PublishError,
    PublishRetriesExhaustedError,
    SourceUnavailableError,
)


logger = logging.getLogger(__name__)

P = ParamSpec("P")
T = TypeVar("T")


# === Retry Decorators ===


def with_source_retry(
    max_attempts: int = 3,
    min_wait: float = 1.0,
    max_wait: float = 30.0,
):
    """
    Retry decorator for signal source operations.

    Retries on SourceUnavailableError with exponential backoff.
    """

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @retry(
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential(multiplier=1, min=min_wait, max=max_wait),
            retry=retry_if_exception_type(SourceUnavailableError),
            before_sleep=before_sleep_log(logger, logging.WARNING),
            reraise=True,
        )
        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            return func(*args, **kwargs)

        return wrapper

    return decorator


def with_publish_retry(
    max_attempts: int = 5,
    min_wait: float = 0.5,
    max_wait: float = 10.0,
):
    """
    Retry decorator for publishing operations.

    Converts RetryError to PublishRetriesExhaustedError.
    """

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @retry(
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential(multiplier=1, min=min_wait, max=max_wait),
            retry=retry_if_exception_type(PublishError),
            before_sleep=before_sleep_log(logger, logging.WARNING),
        )
        def _inner(*args: P.args, **kwargs: P.kwargs) -> T:
            return func(*args, **kwargs)

        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            try:
                return _inner(*args, **kwargs)
            except RetryError as e:
                last_exc = ""
                if e.last_attempt and e.last_attempt.failed:
                    last_exc = str(e.last_attempt.exception())
                raise PublishRetriesExhaustedError(
                    f"Publishing failed after {max_attempts} attempts",
                    attempts=max_attempts,
                    context={"last_exception": last_exc},
                )

        return wrapper

    return decorator


# === Circuit Breaker ===


class CircuitState(Enum):
    CLOSED = "CLOSED"  # Normal operation
    OPEN = "OPEN"  # Failing, reject calls
    HALF_OPEN = "HALF_OPEN"  # Testing if recovered


class CircuitBreaker:
    """
    Circuit breaker pattern implementation.

    Prevents cascading failures by failing fast when a service is down.
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: timedelta | None = None,
        half_open_max_calls: int = 3,
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout or timedelta(seconds=30)
        self.half_open_max_calls = half_open_max_calls
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time: datetime | None = None
        self._half_open_calls = 0
        self._lock = Lock()

    @property
    def state(self) -> CircuitState:
        with self._lock:
            if self._state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    self._state = CircuitState.HALF_OPEN
                    self._half_open_calls = 0
            return self._state

    def _should_attempt_reset(self) -> bool:
        if self._last_failure_time is None:
            return True
        return datetime.utcnow() - self._last_failure_time >= self.recovery_timeout

    def record_success(self) -> None:
        with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                self._half_open_calls += 1
                if self._half_open_calls >= self.half_open_max_calls:
                    self._state = CircuitState.CLOSED
                    self._failure_count = 0
                    logger.info(f"Circuit {self.name} closed after successful recovery")
            elif self._state == CircuitState.CLOSED:
                self._failure_count = 0

    def record_failure(self, exception: Exception) -> None:
        with self._lock:
            self._failure_count += 1
            self._last_failure_time = datetime.utcnow()

            if self._state == CircuitState.HALF_OPEN:
                self._state = CircuitState.OPEN
                logger.warning(
                    f"Circuit {self.name} re-opened after failure in half-open state"
                )
            elif self._failure_count >= self.failure_threshold:
                self._state = CircuitState.OPEN
                logger.warning(
                    f"Circuit {self.name} opened after {self._failure_count} failures"
                )

    def is_available(self) -> bool:
        return self.state != CircuitState.OPEN

    def __call__(self, func: Callable[P, T]) -> Callable[P, T]:
        """Use as decorator."""

        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            if not self.is_available():
                raise SourceUnavailableError(
                    f"Circuit {self.name} is open",
                    context={"circuit_state": self.state.value},
                )
            try:
                result = func(*args, **kwargs)
                self.record_success()
                return result
            except Exception as e:
                self.record_failure(e)
                raise

        return wrapper


def create_source_circuit_breaker(name: str) -> CircuitBreaker:
    """Create a circuit breaker configured for signal sources."""
    return CircuitBreaker(
        name=name,
        failure_threshold=5,
        recovery_timeout=timedelta(seconds=60),
        half_open_max_calls=2,
    )
