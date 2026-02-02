"""
Signal Emitter

Dual-path signal emission with ledger-first invariant.

Guarantees:
- Every signal is written to ledger before hot path push
- Hot path failure does not lose signals (reconcile recovers)
- At-least-once delivery to RiskCast
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Optional

import httpx

from omen.domain.models.omen_signal import OmenSignal
from omen.domain.models.signal_event import SignalEvent, generate_input_event_hash
from omen.infrastructure.ledger import LedgerWriteError, LedgerWriter
from omen.infrastructure.resilience.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerOpen,
    CircuitState,
    register_circuit_breaker,
)

logger = logging.getLogger(__name__)

try:
    from omen.infrastructure.observability.metrics import (
        EMIT_DURATION,
        SIGNALS_EMITTED,
        update_circuit_breaker_state,
    )
    _METRICS_AVAILABLE = True
except ImportError:
    _METRICS_AVAILABLE = False

CIRCUIT_NAME_RISKCAST = "riskcast_hot_path"


class EmitStatus(str, Enum):
    """Emission result status."""

    DELIVERED = "delivered"  # Ledger + hot path success
    LEDGER_ONLY = "ledger_only"  # Ledger success, hot path failed
    DUPLICATE = "duplicate"  # RiskCast already has this signal
    FAILED = "failed"  # Ledger write failed


@dataclass
class EmitResult:
    """Result of signal emission."""

    status: EmitStatus
    signal_id: str
    ledger_partition: Optional[str] = None
    hot_path_ack_id: Optional[str] = None
    error: Optional[str] = None


async def _broadcast_emit_result(event: SignalEvent, result: EmitResult) -> None:
    """Broadcast signal_emitted to WebSocket clients (best effort)."""
    try:
        from omen.api.routes.websocket import broadcast_signal_emitted

        category = (
            getattr(event.signal.category, "value", None)
            or str(event.signal.category)
        )
        await broadcast_signal_emitted(
            signal_id=result.signal_id,
            title=event.signal.title,
            category=category,
            status=result.status.value,
        )
    except Exception as e:
        logger.warning("Failed to broadcast signal event: %s", e)


def _record_emit_metrics(
    event: SignalEvent, result: EmitResult, duration: float
) -> None:
    """Record emit metrics (no-op if prometheus not available)."""
    if not _METRICS_AVAILABLE:
        return
    status = result.status.value
    category = (
        getattr(event.signal.category, "value", None)
        or str(event.signal.category)
    )
    try:
        SIGNALS_EMITTED.labels(status=status, category=category).inc()
        EMIT_DURATION.labels(status=status).observe(duration)
    except Exception as e:
        logger.debug("Emit metrics record failed: %s", e)


@dataclass
class RetryConfig:
    """Retry configuration."""

    max_attempts: int = 5
    base_delay_ms: int = 100
    max_delay_ms: int = 10000
    backoff_multiplier: float = 2.0
    retryable_status_codes: tuple = (408, 429, 500, 502, 503, 504)


class BackpressureController:
    """
    Control emission rate when RiskCast can't keep up.
    """

    def __init__(self, threshold: int = 5, max_backoff_seconds: int = 60):
        self.consecutive_failures = 0
        self.backoff_until: Optional[datetime] = None
        self.threshold = threshold
        self.max_backoff = max_backoff_seconds

    async def wait_if_needed(self) -> None:
        """Wait if in backpressure state."""
        if self.backoff_until and datetime.now(timezone.utc) < self.backoff_until:
            wait_seconds = (self.backoff_until - datetime.now(timezone.utc)).total_seconds()
            logger.warning("Backpressure: waiting %.1fs", wait_seconds)
            await asyncio.sleep(wait_seconds)

    def record_success(self) -> None:
        """Record successful delivery."""
        self.consecutive_failures = 0
        self.backoff_until = None

    def record_failure(self) -> None:
        """Record failed delivery."""
        self.consecutive_failures += 1
        if self.consecutive_failures >= self.threshold:
            backoff = min(self.max_backoff, 2**self.consecutive_failures)
            self.backoff_until = datetime.now(timezone.utc) + timedelta(seconds=backoff)
            logger.warning("Entering backpressure: %ss", backoff)


class HotPathError(Exception):
    """Hot path delivery failed."""

    pass


class DuplicateSignalError(Exception):
    """Signal already processed by RiskCast (409)."""

    def __init__(self, signal_id: str, ack_id: Optional[str] = None):
        super().__init__(signal_id)
        self.signal_id = signal_id
        self.ack_id = ack_id


class SignalEmitter:
    """
    Dual-path signal emitter.

    CRITICAL INVARIANT:
    Signal MUST be written to ledger BEFORE hot path push.
    This ensures reconcile can always recover from hot path failures.
    """

    def __init__(
        self,
        ledger: LedgerWriter,
        riskcast_url: str,
        api_key: str,
        retry_config: Optional[RetryConfig] = None,
        circuit_breaker_config: Optional[CircuitBreakerConfig] = None,
    ):
        self.ledger = ledger
        self.riskcast_url = riskcast_url.rstrip("/")
        self.api_key = api_key
        self.retry_config = retry_config or RetryConfig()
        self.backpressure = BackpressureController()
        self._client: Optional[httpx.AsyncClient] = None

        self._circuit_breaker = CircuitBreaker(
            name=CIRCUIT_NAME_RISKCAST,
            config=circuit_breaker_config
            or CircuitBreakerConfig(
                failure_threshold=5,
                success_threshold=3,
                timeout_seconds=30.0,
                failure_rate_threshold=0.5,
            ),
            on_state_change=self._on_circuit_state_change,
        )
        register_circuit_breaker(CIRCUIT_NAME_RISKCAST, self._circuit_breaker)
        if _METRICS_AVAILABLE:
            update_circuit_breaker_state(CIRCUIT_NAME_RISKCAST, "closed")

    def _on_circuit_state_change(
        self, old_state: CircuitState, new_state: CircuitState
    ) -> None:
        if new_state == CircuitState.OPEN:
            logger.warning(
                "RiskCast circuit OPENED - hot path disabled, "
                "signals will be LEDGER_ONLY until recovery"
            )
        elif new_state == CircuitState.CLOSED:
            logger.info("RiskCast circuit CLOSED - hot path restored")

    async def __aenter__(self):
        self._client = httpx.AsyncClient(timeout=30.0)
        return self

    async def __aexit__(self, *args):
        await self.close()

    async def close(self) -> None:
        """
        Close HTTP client and release resources. Called during graceful shutdown.

        Ensures:
        - HTTP client connections are closed
        - Resources are released
        """
        if self._client:
            try:
                await self._client.aclose()
                logger.info("SignalEmitter: HTTP client closed.")
            except Exception as e:
                logger.warning("SignalEmitter: error closing client: %s", e)
            self._client = None

    async def emit(
        self,
        signal: OmenSignal,
        input_event: dict,
        observed_at: datetime,
    ) -> EmitResult:
        """
        Emit signal via dual-path.

        1. Write to ledger (MUST succeed)
        2. Push to hot path (best effort)

        Args:
            signal: OmenSignal to emit
            input_event: Raw input event (for hash)
            observed_at: When input was observed

        Returns:
            EmitResult with status and metadata
        """
        start = time.perf_counter()
        input_hash = generate_input_event_hash(input_event)
        event = SignalEvent.from_omen_signal(
            signal=signal,
            input_event_hash=input_hash,
            observed_at=observed_at,
        )

        # === STEP 1: Write to ledger (MUST succeed) ===
        try:
            event = self.ledger.write(event)
            logger.info(
                "Ledger write OK: %s -> %s",
                event.signal_id,
                event.ledger_partition,
            )
        except LedgerWriteError as e:
            logger.error("Ledger write FAILED: %s", e)
            result = EmitResult(
                status=EmitStatus.FAILED,
                signal_id=event.signal_id,
                error=str(e),
            )
            asyncio.create_task(_broadcast_emit_result(event, result))
            return result
        except Exception as e:
            logger.exception("Ledger write failed: %s", e)
            result = EmitResult(
                status=EmitStatus.FAILED,
                signal_id=event.signal_id,
                error=str(e),
            )
            asyncio.create_task(_broadcast_emit_result(event, result))
            return result

        # === STEP 2: Push to hot path (best effort) with circuit breaker ===
        await self.backpressure.wait_if_needed()

        try:
            kind, ack_id = await self._circuit_breaker.call(
                self._push_to_riskcast_wrapped, event
            )
            self.backpressure.record_success()
            if kind == "duplicate":
                logger.info("Duplicate signal (already processed): %s", event.signal_id)
                result = EmitResult(
                    status=EmitStatus.DUPLICATE,
                    signal_id=event.signal_id,
                    ledger_partition=event.ledger_partition,
                    hot_path_ack_id=ack_id,
                )
                _record_emit_metrics(event, result, time.perf_counter() - start)
                asyncio.create_task(_broadcast_emit_result(event, result))
                return result
            result = EmitResult(
                status=EmitStatus.DELIVERED,
                signal_id=event.signal_id,
                ledger_partition=event.ledger_partition,
                hot_path_ack_id=ack_id,
            )
            _record_emit_metrics(event, result, time.perf_counter() - start)
            asyncio.create_task(_broadcast_emit_result(event, result))
            return result
        except CircuitBreakerOpen as e:
            logger.warning(
                "Circuit breaker open for %s, returning LEDGER_ONLY (retry after %.1fs)",
                event.signal_id,
                e.retry_after,
            )
            result = EmitResult(
                status=EmitStatus.LEDGER_ONLY,
                signal_id=event.signal_id,
                ledger_partition=event.ledger_partition,
                error=f"Circuit open, retry after {e.retry_after:.1f}s",
            )
            _record_emit_metrics(event, result, time.perf_counter() - start)
            asyncio.create_task(_broadcast_emit_result(event, result))
            return result
        except HotPathError as e:
            self.backpressure.record_failure()
            logger.warning("Hot path failed (will reconcile): %s", e)
            result = EmitResult(
                status=EmitStatus.LEDGER_ONLY,
                signal_id=event.signal_id,
                ledger_partition=event.ledger_partition,
                error=str(e),
            )
            _record_emit_metrics(event, result, time.perf_counter() - start)
            asyncio.create_task(_broadcast_emit_result(event, result))
            return result

    async def _push_to_riskcast_wrapped(
        self, event: SignalEvent
    ) -> tuple[str, Optional[str]]:
        """
        Wrapper for circuit breaker: returns (kind, ack_id) so 409 counts as success.
        kind is "delivered" or "duplicate".
        """
        try:
            ack_id = await self._push_to_riskcast(event)
            return ("delivered", ack_id)
        except DuplicateSignalError as e:
            return ("duplicate", e.ack_id)

    async def _push_to_riskcast(self, event: SignalEvent) -> str:
        """
        Push signal to RiskCast with retry.

        Returns:
            ack_id from RiskCast

        Raises:
            DuplicateSignalError: If 409 (already processed)
            HotPathError: If all retries exhausted
        """
        url = f"{self.riskcast_url}/api/v1/signals/ingest"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "X-Idempotency-Key": event.signal_id,
        }
        body = event.model_dump_json()

        last_error: Optional[str] = None

        for attempt in range(self.retry_config.max_attempts):
            try:
                response = await self._client.post(
                    url,
                    content=body,
                    headers=headers,
                )

                if response.status_code == 200:
                    data = response.json()
                    return data.get("ack_id", "unknown")

                if response.status_code == 409:
                    data = response.json()
                    raise DuplicateSignalError(
                        event.signal_id,
                        ack_id=data.get("ack_id"),
                    )

                if response.status_code in self.retry_config.retryable_status_codes:
                    last_error = f"HTTP {response.status_code}: {response.text[:200]}"
                    await self._wait_before_retry(attempt)
                    continue

                raise HotPathError(
                    f"HTTP {response.status_code}: {response.text[:200]}"
                )

            except httpx.RequestError as e:
                last_error = str(e)
                await self._wait_before_retry(attempt)

        raise HotPathError(f"Max retries exceeded: {last_error}")

    async def _wait_before_retry(self, attempt: int) -> None:
        """Calculate and wait for retry backoff."""
        delay_ms = min(
            self.retry_config.base_delay_ms
            * (self.retry_config.backoff_multiplier**attempt),
            self.retry_config.max_delay_ms,
        )
        await asyncio.sleep(delay_ms / 1000)

    @property
    def circuit_breaker_stats(self):
        """Return circuit breaker statistics for monitoring."""
        return self._circuit_breaker.stats
