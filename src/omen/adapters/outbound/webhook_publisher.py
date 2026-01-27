"""Webhook output publisher (with retry, redaction, and optional signature)."""

import json
import time

import httpx

from omen.application.ports.output_publisher import OutputPublisher
from omen.domain.errors import PublishError
from omen.domain.models.omen_signal import OmenSignal
from omen.infrastructure.security.auth import generate_webhook_signature
from omen.infrastructure.security.redaction import redact_for_webhook


class WebhookPublisher(OutputPublisher):
    """
    Publish signals to a webhook endpoint.

    Features:
    - HMAC signature when secret is set
    - Retry with exponential backoff
    - Field redaction for external consumption
    """

    def __init__(
        self,
        url: str,
        secret: str | None = None,
        timeout: int = 30,
        max_retries: int = 3,
    ):
        self._url = url
        self._secret = secret
        self._timeout = timeout
        self._max_retries = max_retries
        self._client = httpx.Client(timeout=timeout)

    def publish(self, signal: OmenSignal) -> bool:
        """Publish signal to webhook (sync, with retry)."""
        payload = redact_for_webhook(signal)
        payload_bytes = json.dumps(payload, default=str).encode()
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self._secret:
            headers["X-OMEN-Signature"] = generate_webhook_signature(
                payload_bytes, self._secret
            )
        last_error: Exception | None = None
        for attempt in range(self._max_retries):
            try:
                response = self._client.post(
                    self._url,
                    content=payload_bytes,
                    headers=headers,
                )
                response.raise_for_status()
                return True
            except (httpx.HTTPError, httpx.HTTPStatusError) as e:
                last_error = e
                if attempt < self._max_retries - 1:
                    time.sleep(2**attempt)
        raise PublishError(
            f"Webhook failed after {self._max_retries} attempts: {last_error}",
            context={"signal_id": signal.signal_id},
        )

    async def publish_async(self, signal: OmenSignal) -> bool:
        """Async publish (delegates to sync)."""
        return self.publish(signal)
