"""Polymarket API client (stub implementation with retry and circuit breaker)."""

import httpx
from typing import Any, AsyncIterator

from omen.adapters.inbound.polymarket.schemas import PolymarketEvent
from omen.config import settings
from omen.domain.errors import (
    SourceRateLimitedError,
    SourceUnavailableError,
)
from omen.infrastructure.retry import (
    create_source_circuit_breaker,
    with_source_retry,
)


class PolymarketClient:
    """Client for Polymarket API (stub)."""

    def __init__(self, api_url: str | None = None, api_key: str | None = None):
        self.api_url = api_url or getattr(
            settings, "polymarket_api_url", "https://api.polymarket.com"
        )
        self.api_key = api_key or getattr(settings, "polymarket_api_key", "")
        self._circuit = create_source_circuit_breaker("polymarket")
        self._headers = (
            {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
        )
        self.client = httpx.AsyncClient(
            base_url=self.api_url,
            headers=self._headers,
        )

    @with_source_retry(max_attempts=3, min_wait=1.0, max_wait=30.0)
    def fetch_markets(self, limit: int = 100) -> list[dict[str, Any]]:
        """
        Fetch markets with retry and circuit breaker (sync).

        Raises SourceUnavailableError if circuit is open or request fails.
        """
        if not self._circuit.is_available():
            raise SourceUnavailableError(
                "Polymarket circuit is open",
                context={"circuit_state": self._circuit.state.value},
            )
        try:
            with httpx.Client(
                base_url=self.api_url,
                headers=self._headers,
                timeout=30.0,
            ) as client:
                response = client.get(
                    "/markets",
                    params={"limit": limit},
                )
                response.raise_for_status()
                self._circuit.record_success()
                return response.json() if response.content else []
        except httpx.TimeoutException as e:
            self._circuit.record_failure(e)
            raise SourceUnavailableError(
                f"Polymarket timeout: {e}",
                context={"event": "timeout"},
            )
        except httpx.HTTPStatusError as e:
            self._circuit.record_failure(e)
            if e.response.status_code == 429:
                retry_after = int(
                    e.response.headers.get("Retry-After", "60")
                )
                raise SourceRateLimitedError(
                    "Rate limited",
                    retry_after_seconds=retry_after,
                    context={"status_code": 429},
                )
            raise SourceUnavailableError(
                f"Polymarket HTTP error: {e}",
                context={"status_code": e.response.status_code},
            )
        except Exception as e:
            self._circuit.record_failure(e)
            raise SourceUnavailableError(
                f"Polymarket error: {e}",
                context={"exception_type": type(e).__name__},
            )

    async def fetch_events(self) -> AsyncIterator[PolymarketEvent]:
        """
        Fetch events from Polymarket API (async stub).

        Stub: yields nothing. Production would use fetch_markets and map.
        """
        return
        yield  # makes this an async generator

    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.aclose()
