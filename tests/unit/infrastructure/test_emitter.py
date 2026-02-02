"""Unit tests for SignalEmitter (dual-path, ledger-first)."""

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from omen.domain.models.omen_signal import (
    OmenSignal,
    ConfidenceLevel,
    SignalCategory,
    GeographicContext,
    TemporalContext,
)
from omen.domain.models.impact_hints import ImpactHints
from omen.domain.models.signal_event import SignalEvent
from omen.domain.models.enums import SignalType, SignalStatus
from omen.infrastructure.ledger import LedgerWriter
from omen.infrastructure.emitter import (
    SignalEmitter,
    EmitResult,
    EmitStatus,
    HotPathError,
    DuplicateSignalError,
)


def _make_minimal_signal(signal_id: str = "OMEN-EMIT001") -> OmenSignal:
    """Minimal OmenSignal for emitter tests."""
    return OmenSignal(
        signal_id=signal_id,
        source_event_id="emit-test",
        trace_id="trace-emit",
        title="Emit Test",
        probability=0.5,
        probability_source="test",
        confidence_score=0.7,
        confidence_level=ConfidenceLevel.MEDIUM,
        confidence_factors={},
        category=SignalCategory.OTHER,
        geographic=GeographicContext(),
        temporal=TemporalContext(),
        impact_hints=ImpactHints(),
        evidence=[],
        ruleset_version="1.0.0",
        generated_at=datetime.now(timezone.utc),
        signal_type=SignalType.UNCLASSIFIED,
        status=SignalStatus.ACTIVE,
    )


@pytest.mark.asyncio
async def test_ledger_first_invariant_hot_path_fails(tmp_path: Path):
    """Ledger write succeeds; hot path fails -> LEDGER_ONLY."""
    ledger = LedgerWriter(tmp_path)
    async with SignalEmitter(
        ledger=ledger,
        riskcast_url="http://localhost:9999",
        api_key="test-key",
    ) as emitter:
        mock_response = MagicMock()
        mock_response.status_code = 503
        mock_response.text = "Unavailable"
        emitter._client.post = AsyncMock(return_value=mock_response)

        result = await emitter.emit(
            signal=_make_minimal_signal(),
            input_event={"test": "data"},
            observed_at=datetime.now(timezone.utc),
        )

    assert result.status == EmitStatus.LEDGER_ONLY
    assert result.signal_id == "OMEN-EMIT001"
    assert result.ledger_partition is not None
    assert result.error is not None


@pytest.mark.asyncio
async def test_delivered_when_riskcast_returns_200(tmp_path: Path):
    """Ledger + hot path success -> DELIVERED with ack_id."""
    ledger = LedgerWriter(tmp_path)
    async with SignalEmitter(
        ledger=ledger,
        riskcast_url="http://localhost:9999",
        api_key="test-key",
    ) as emitter:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json = MagicMock(return_value={"ack_id": "riskcast-ack-123"})
        emitter._client.post = AsyncMock(return_value=mock_response)

        result = await emitter.emit(
            signal=_make_minimal_signal("OMEN-DELIVERED"),
            input_event={"k": "v"},
            observed_at=datetime.now(timezone.utc),
        )

    assert result.status == EmitStatus.DELIVERED
    assert result.signal_id == "OMEN-DELIVERED"
    assert result.ledger_partition is not None
    assert result.hot_path_ack_id == "riskcast-ack-123"


@pytest.mark.asyncio
async def test_duplicate_when_riskcast_returns_409(tmp_path: Path):
    """Hot path 409 -> DUPLICATE (ledger still written)."""
    ledger = LedgerWriter(tmp_path)
    async with SignalEmitter(
        ledger=ledger,
        riskcast_url="http://localhost:9999",
        api_key="test-key",
    ) as emitter:
        mock_response = MagicMock()
        mock_response.status_code = 409
        mock_response.text = "Conflict"
        emitter._client.post = AsyncMock(return_value=mock_response)

        result = await emitter.emit(
            signal=_make_minimal_signal("OMEN-DUP"),
            input_event={"id": "dup"},
            observed_at=datetime.now(timezone.utc),
        )

    assert result.status == EmitStatus.DUPLICATE
    assert result.signal_id == "OMEN-DUP"
    assert result.ledger_partition is not None


@pytest.mark.asyncio
async def test_ledger_write_failure_returns_failed(tmp_path: Path):
    """If ledger write fails -> FAILED, no hot path attempt."""
    ledger = LedgerWriter(tmp_path)

    def failing_write(event: SignalEvent) -> SignalEvent:
        from omen.infrastructure.ledger import LedgerWriteError

        raise LedgerWriteError("simulated failure")

    ledger.write = failing_write

    async with SignalEmitter(
        ledger=ledger,
        riskcast_url="http://localhost:9999",
        api_key="test-key",
    ) as emitter:
        result = await emitter.emit(
            signal=_make_minimal_signal("OMEN-FAIL"),
            input_event={"x": 1},
            observed_at=datetime.now(timezone.utc),
        )

    assert result.status == EmitStatus.FAILED
    assert result.signal_id == "OMEN-FAIL"
    assert result.ledger_partition is None
    assert "simulated" in (result.error or "")


@pytest.mark.asyncio
async def test_backpressure_record_success_resets_failures(tmp_path: Path):
    """Backpressure consecutive_failures reset on success."""
    ledger = LedgerWriter(tmp_path)
    async with SignalEmitter(
        ledger=ledger,
        riskcast_url="http://localhost:9999",
        api_key="test-key",
    ) as emitter:
        mock_ok = MagicMock()
        mock_ok.status_code = 200
        mock_ok.json = MagicMock(return_value={"ack_id": "ok"})
        emitter._client.post = AsyncMock(return_value=mock_ok)
        await emitter.emit(
            signal=_make_minimal_signal("OMEN-BP1"),
            input_event={},
            observed_at=datetime.now(timezone.utc),
        )
    assert emitter.backpressure.consecutive_failures == 0
    assert emitter.backpressure.backoff_until is None


@pytest.mark.asyncio
async def test_retry_config_used(tmp_path: Path):
    """Retry config limits attempts (quick fail with non-retryable code)."""
    from omen.infrastructure.emitter import RetryConfig

    ledger = LedgerWriter(tmp_path)
    config = RetryConfig(max_attempts=2, base_delay_ms=1, max_delay_ms=2)
    async with SignalEmitter(
        ledger=ledger,
        riskcast_url="http://localhost:9999",
        api_key="test-key",
        retry_config=config,
    ) as emitter:
        mock_response = MagicMock()
        mock_response.status_code = 502
        mock_response.text = "Bad Gateway"
        emitter._client.post = AsyncMock(return_value=mock_response)

        result = await emitter.emit(
            signal=_make_minimal_signal("OMEN-RETRY"),
            input_event={},
            observed_at=datetime.now(timezone.utc),
        )
        post_call_count = emitter._client.post.call_count

    assert result.status == EmitStatus.LEDGER_ONLY
    assert result.ledger_partition is not None
    # Should have tried 2 times (max_attempts)
    assert post_call_count == 2


@pytest.mark.asyncio
async def test_ledger_only_when_circuit_open(tmp_path: Path):
    """When circuit breaker is OPEN, emit returns LEDGER_ONLY without calling RiskCast."""
    ledger = LedgerWriter(tmp_path)
    from omen.infrastructure.resilience.circuit_breaker import (
        CircuitBreakerConfig,
        CircuitState,
    )

    config = CircuitBreakerConfig(failure_threshold=1, timeout_seconds=60.0)
    async with SignalEmitter(
        ledger=ledger,
        riskcast_url="http://localhost:9999",
        api_key="test-key",
        circuit_breaker_config=config,
    ) as emitter:
        # Open the circuit with one failure
        mock_fail = MagicMock()
        mock_fail.status_code = 503
        mock_fail.text = "Unavailable"
        emitter._client.post = AsyncMock(return_value=mock_fail)
        await emitter.emit(
            signal=_make_minimal_signal("OMEN-FAIL1"),
            input_event={},
            observed_at=datetime.now(timezone.utc),
        )
        assert emitter._circuit_breaker.state == CircuitState.OPEN

        # Next emit should return LEDGER_ONLY without calling post again
        post_before = emitter._client.post.call_count
        result = await emitter.emit(
            signal=_make_minimal_signal("OMEN-FAIL2"),
            input_event={},
            observed_at=datetime.now(timezone.utc),
        )
        post_after = emitter._client.post.call_count

    assert result.status == EmitStatus.LEDGER_ONLY
    assert result.ledger_partition is not None
    assert "Circuit open" in (result.error or "")
    # Circuit was open: no additional HTTP call for second emit
    assert post_after == post_before
