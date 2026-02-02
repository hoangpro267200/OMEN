"""Unit tests for async Circuit Breaker (emitter hot path)."""

import asyncio

import pytest

from omen.infrastructure.resilience.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerOpen,
    CircuitState,
)


@pytest.mark.asyncio
async def test_circuit_opens_after_consecutive_failures():
    """Circuit opens after failure_threshold consecutive failures."""
    cb = CircuitBreaker(
        "test",
        CircuitBreakerConfig(failure_threshold=3, timeout_seconds=1.0),
    )

    async def failing_func():
        raise Exception("fail")

    for _ in range(3):
        with pytest.raises(Exception, match="fail"):
            await cb.call(failing_func)

    assert cb.state == CircuitState.OPEN

    with pytest.raises(CircuitBreakerOpen) as exc_info:
        await cb.call(failing_func)

    assert exc_info.value.circuit_name == "test"
    assert exc_info.value.retry_after > 0


@pytest.mark.asyncio
async def test_circuit_transitions_to_half_open_after_timeout():
    """Circuit transitions to HALF_OPEN after timeout."""
    cb = CircuitBreaker(
        "test",
        CircuitBreakerConfig(failure_threshold=1, timeout_seconds=0.1),
    )

    async def failing_func():
        raise Exception("fail")

    with pytest.raises(Exception):
        await cb.call(failing_func)

    assert cb.state == CircuitState.OPEN

    await asyncio.sleep(0.15)

    async def success_func():
        return "ok"

    result = await cb.call(success_func)
    assert result == "ok"
    assert cb.state in (CircuitState.HALF_OPEN, CircuitState.CLOSED)


@pytest.mark.asyncio
async def test_circuit_closes_after_successes_in_half_open():
    """Circuit closes after success_threshold successes in HALF_OPEN."""
    cb = CircuitBreaker(
        "test",
        CircuitBreakerConfig(
            failure_threshold=1,
            success_threshold=2,
            timeout_seconds=0.1,
        ),
    )

    async def failing_func():
        raise Exception("fail")

    async def success_func():
        return "ok"

    with pytest.raises(Exception):
        await cb.call(failing_func)

    await asyncio.sleep(0.15)

    await cb.call(success_func)
    await cb.call(success_func)

    assert cb.state == CircuitState.CLOSED


@pytest.mark.asyncio
async def test_circuit_reopens_on_failure_in_half_open():
    """Circuit reopens if failure occurs in HALF_OPEN."""
    cb = CircuitBreaker(
        "test",
        CircuitBreakerConfig(failure_threshold=1, timeout_seconds=0.1),
    )

    call_count = 0

    async def flaky_func():
        nonlocal call_count
        call_count += 1
        if call_count <= 2:
            raise Exception("fail")
        return "ok"

    with pytest.raises(Exception):
        await cb.call(flaky_func)

    assert cb.state == CircuitState.OPEN

    await asyncio.sleep(0.15)

    with pytest.raises(Exception):
        await cb.call(flaky_func)

    assert cb.state == CircuitState.OPEN


@pytest.mark.asyncio
async def test_circuit_stats_updated():
    """Stats reflect calls, failures, and state."""
    cb = CircuitBreaker(
        "test",
        CircuitBreakerConfig(failure_threshold=2, timeout_seconds=10.0),
    )

    async def failing_func():
        raise Exception("fail")

    with pytest.raises(Exception):
        await cb.call(failing_func)
    with pytest.raises(Exception):
        await cb.call(failing_func)

    stats = cb.stats
    assert stats.state == CircuitState.OPEN
    assert stats.total_calls == 2
    assert stats.total_failures == 2
    assert stats.consecutive_failures == 2

    with pytest.raises(CircuitBreakerOpen):
        await cb.call(failing_func)

    stats = cb.stats
    assert stats.total_rejected == 1


@pytest.mark.asyncio
async def test_circuit_manual_reset():
    """Manual reset closes the circuit."""
    cb = CircuitBreaker(
        "test",
        CircuitBreakerConfig(failure_threshold=1, timeout_seconds=10.0),
    )

    async def failing_func():
        raise Exception("fail")

    with pytest.raises(Exception):
        await cb.call(failing_func)
    assert cb.state == CircuitState.OPEN

    await cb.reset()
    assert cb.state == CircuitState.CLOSED

    async def success_func():
        return "ok"

    result = await cb.call(success_func)
    assert result == "ok"
