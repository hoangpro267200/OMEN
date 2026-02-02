"""Webhook output publisher (with retry, redaction, and optional signature)."""

import asyncio
import json
import time
from typing import Optional

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
    - Proper async support (non-blocking)
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
        self._async_client: Optional[httpx.AsyncClient] = None

    def _get_async_client(self) -> httpx.AsyncClient:
        """Get or create async HTTP client."""
        if self._async_client is None:
            self._async_client = httpx.AsyncClient(timeout=self._timeout)
        return self._async_client

    def _prepare_request(self, signal: OmenSignal) -> tuple[bytes, dict[str, str]]:
        """Prepare payload and headers for webhook request."""
        payload = redact_for_webhook(signal)
        payload_bytes = json.dumps(payload, default=str).encode()
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self._secret:
            headers["X-OMEN-Signature"] = generate_webhook_signature(
                payload_bytes, self._secret
            )
        return payload_bytes, headers

    def publish(self, signal: OmenSignal) -> bool:
        """Publish signal to webhook (sync, with retry)."""
        payload_bytes, headers = self._prepare_request(signal)
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
        """
        Async publish with non-blocking retry.
        
        Uses httpx.AsyncClient for proper async I/O.
        Does NOT block the event loop.
        """
        payload_bytes, headers = self._prepare_request(signal)
        client = self._get_async_client()
        last_error: Exception | None = None
        
        for attempt in range(self._max_retries):
            try:
                response = await client.post(
                    self._url,
                    content=payload_bytes,
                    headers=headers,
                )
                response.raise_for_status()
                return True
            except (httpx.HTTPError, httpx.HTTPStatusError) as e:
                last_error = e
                if attempt < self._max_retries - 1:
                    # Non-blocking sleep
                    await asyncio.sleep(2**attempt)
        
        raise PublishError(
            f"Webhook failed after {self._max_retries} attempts: {last_error}",
            context={"signal_id": signal.signal_id},
        )

    async def close(self) -> None:
        """Close HTTP clients and release resources."""
        if self._async_client:
            await self._async_client.aclose()
            self._async_client = None
        self._client.close()
