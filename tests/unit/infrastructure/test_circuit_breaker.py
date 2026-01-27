"""Tests for circuit breaker."""

from datetime import timedelta

import pytest

from omen.domain.errors import SourceUnavailableError
from omen.infrastructure.retry import CircuitBreaker, CircuitState, create_source_circuit_breaker


class TestCircuitBreaker:
    """Circuit opens after threshold failures and recovers after timeout."""

    def test_starts_closed(self):
        cb = CircuitBreaker("test", failure_threshold=3)
        assert cb.state == CircuitState.CLOSED
        assert cb.is_available() is True

    def test_opens_after_failure_threshold(self):
        cb = CircuitBreaker("test", failure_threshold=3)
        cb.record_failure(ValueError("x"))
        cb.record_failure(ValueError("x"))
        assert cb.state == CircuitState.CLOSED
        cb.record_failure(ValueError("x"))
        assert cb.state == CircuitState.OPEN
        assert cb.is_available() is False

    def test_decorator_raises_when_open(self):
        cb = CircuitBreaker("test", failure_threshold=1)
        cb.record_failure(ValueError("x"))
        assert cb.state == CircuitState.OPEN

        @cb
        def call() -> str:
            return "ok"

        with pytest.raises(SourceUnavailableError, match="open"):
            call()

    def test_decorator_records_success_and_failure(self):
        cb = CircuitBreaker("test", failure_threshold=2)
        call_count = 0

        @cb
        def flaky() -> str:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ValueError("first")
            return "ok"

        with pytest.raises(ValueError, match="first"):
            flaky()
        assert cb.state == CircuitState.CLOSED
        assert flaky() == "ok"
        assert call_count == 2

    def test_create_source_circuit_breaker_has_sensible_defaults(self):
        cb = create_source_circuit_breaker("polymarket")
        assert cb.name == "polymarket"
        assert cb.failure_threshold == 5
        assert cb.recovery_timeout == timedelta(seconds=60)
        assert cb.half_open_max_calls == 2
