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
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional

import httpx

from omen.domain.models.omen_signal import OmenSignal
from omen.domain.models.signal_event import SignalEvent, generate_input_event_hash
from omen.infrastructure.ledger import LedgerWriteError, LedgerWriter

logger = logging.getLogger(__name__)


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
        if self.backoff_until and datetime.utcnow() < self.backoff_until:
            wait_seconds = (self.backoff_until - datetime.utcnow()).total_seconds()
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
            self.backoff_until = datetime.utcnow() + timedelta(seconds=backoff)
            logger.warning("Entering backpressure: %ss", backoff)


class HotPathError(Exception):
    """Hot path delivery failed."""

    pass


class DuplicateSignalError(Exception):
    """Signal already processed by RiskCast."""

    pass


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
    ):
        self.ledger = ledger
        self.riskcast_url = riskcast_url.rstrip("/")
        self.api_key = api_key
        self.retry_config = retry_config or RetryConfig()
        self.backpressure = BackpressureController()
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        self._client = httpx.AsyncClient(timeout=30.0)
        return self

    async def __aexit__(self, *args):
        if self._client:
            await self._client.aclose()

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
            return EmitResult(
                status=EmitStatus.FAILED,
                signal_id=event.signal_id,
                error=str(e),
            )
        except Exception as e:
            logger.exception("Ledger write failed: %s", e)
            return EmitResult(
                status=EmitStatus.FAILED,
                signal_id=event.signal_id,
                error=str(e),
            )

        # === STEP 2: Push to hot path (best effort) ===
        await self.backpressure.wait_if_needed()

        try:
            ack_id = await self._push_to_riskcast(event)
            self.backpressure.record_success()
            return EmitResult(
                status=EmitStatus.DELIVERED,
                signal_id=event.signal_id,
                ledger_partition=event.ledger_partition,
                hot_path_ack_id=ack_id,
            )
        except DuplicateSignalError:
            logger.info("Duplicate signal (already processed): %s", event.signal_id)
            return EmitResult(
                status=EmitStatus.DUPLICATE,
                signal_id=event.signal_id,
                ledger_partition=event.ledger_partition,
            )
        except HotPathError as e:
            self.backpressure.record_failure()
            logger.warning("Hot path failed (will reconcile): %s", e)
            return EmitResult(
                status=EmitStatus.LEDGER_ONLY,
                signal_id=event.signal_id,
                ledger_partition=event.ledger_partition,
                error=str(e),
            )

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
                    raise DuplicateSignalError(event.signal_id)

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
