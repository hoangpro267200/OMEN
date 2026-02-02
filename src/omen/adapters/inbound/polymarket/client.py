"""Polymarket legacy API client (configurable URL + optional API key)."""

import logging
from typing import Any, AsyncIterator

import httpx

from omen.adapters.inbound.polymarket.schemas import PolymarketEvent
from omen.domain.errors import SourceRateLimitedError, SourceUnavailableError
from omen.infrastructure.retry import create_source_circuit_breaker
from omen.polymarket_settings import get_polymarket_settings
from omen.adapters.inbound.polymarket.http_retry import run_with_retry

logger = logging.getLogger(__name__)


class PolymarketClient:
    """
    Client for Polymarket legacy API.

    URL from POLYMARKET_API_URL; key from POLYMARKET_API_KEY.
    Auth: Authorization: Bearer <key> when key is set. Public endpoints work without key.
    On 401/403 without key we log "missing key".
    """

    def __init__(self, api_url: str | None = None, api_key: str | None = None):
        s = get_polymarket_settings()
        self.api_url = (api_url or s.api_url).rstrip("/")
        self.api_key = api_key if api_key is not None else (s.api_key or "")
        self._circuit = create_source_circuit_breaker("polymarket")
        self._headers: dict[str, str] = {"User-Agent": s.user_agent}
        if self.api_key:
            self._headers["Authorization"] = f"Bearer {self.api_key}"
        self._timeout = s.timeout_s
        self._trust_env = s.httpx_trust_env
        self.client = httpx.AsyncClient(
            base_url=self.api_url,
            headers=self._headers,
            timeout=self._timeout,
            trust_env=self._trust_env,
        )

    def fetch_markets(self, limit: int = 100) -> list[dict[str, Any]]:
        """
        Fetch markets with retry and circuit breaker (sync).

        Raises SourceUnavailableError if circuit is open or request fails.
        On 401/403 without API key, logs "missing key" and raises.
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
                timeout=self._timeout,
                trust_env=self._trust_env,
            ) as client:

                def do_request() -> httpx.Response:
                    return client.get("/markets", params={"limit": limit})

                response = run_with_retry(do_request)
                if response.status_code in (401, 403) and not self.api_key:
                    logger.warning(
                        "Polymarket returned %s: missing API key. Set POLYMARKET_API_KEY for protected endpoints.",
                        response.status_code,
                    )
                response.raise_for_status()
                self._circuit.record_success()
                return response.json() if response.content else []
        except httpx.HTTPStatusError as e:
            self._circuit.record_failure(e)
            if e.response.status_code in (401, 403) and not self.api_key:
                logger.warning(
                    "Polymarket %s: missing key (POLYMARKET_API_KEY not set)",
                    e.response.status_code,
                )
            if e.response.status_code == 429:
                retry_after = int(e.response.headers.get("Retry-After", "60"))
                raise SourceRateLimitedError(
                    "Rate limited",
                    retry_after_seconds=retry_after,
                    context={"status_code": 429},
                ) from e
            raise SourceUnavailableError(
                f"Polymarket HTTP error: {e}",
                context={"status_code": e.response.status_code},
            ) from e
        except SourceUnavailableError:
            raise
        except SourceRateLimitedError:
            raise
        except Exception as e:
            self._circuit.record_failure(e)
            raise SourceUnavailableError(
                f"Polymarket error: {e}",
                context={"exception_type": type(e).__name__},
            ) from e

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
