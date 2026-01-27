"""
Live Polymarket API client (Gamma API).

Base URL: https://gamma-api.polymarket.com
No API key required for public read endpoints.
"""

from typing import Any

import httpx

from omen.domain.errors import SourceRateLimitedError, SourceUnavailableError
from omen.infrastructure.retry import create_source_circuit_breaker


class PolymarketLiveClient:
    """
    Client for Polymarket Gamma API (live event/market data).

    Use for demo and live integrations. For existing tests, the original
    PolymarketClient remains unchanged.
    """

    GAMMA_BASE_URL = "https://gamma-api.polymarket.com"
    CLOB_BASE_URL = "https://clob.polymarket.com"

    def __init__(
        self,
        timeout: float = 30.0,
        use_gamma: bool = True,
    ):
        self._timeout = timeout
        self._base_url = self.GAMMA_BASE_URL if use_gamma else self.CLOB_BASE_URL
        self._circuit = create_source_circuit_breaker("polymarket_live")
        self._client = httpx.Client(timeout=timeout)

    def fetch_events(
        self,
        limit: int = 50,
        active: bool = True,
        closed: bool = False,
    ) -> list[dict[str, Any]]:
        """
        Fetch events from Polymarket Gamma API.

        Returns list of event dicts with nested markets.
        """
        if not self._circuit.is_available():
            raise SourceUnavailableError(
                "Polymarket circuit breaker is open",
                context={"circuit_state": self._circuit.state.value},
            )
        try:
            params: dict[str, Any] = {"limit": limit}
            if self._base_url == self.GAMMA_BASE_URL:
                params["active"] = str(active).lower()
                params["closed"] = str(closed).lower()
            response = self._client.get(
                f"{self._base_url}/events",
                params=params,
            )
            response.raise_for_status()
            self._circuit.record_success()
            data = response.json()
            return data if isinstance(data, list) else []
        except httpx.TimeoutException as e:
            self._circuit.record_failure(e)
            raise SourceUnavailableError(
                f"Polymarket timeout: {e}",
                context={"event": "timeout"},
            ) from e
        except httpx.HTTPStatusError as e:
            self._circuit.record_failure(e)
            if e.response.status_code == 429:
                retry_after = int(e.response.headers.get("Retry-After", "60"))
                raise SourceRateLimitedError(
                    "Polymarket rate limited",
                    retry_after_seconds=retry_after,
                    context={"status_code": 429},
                ) from e
            raise SourceUnavailableError(
                f"Polymarket HTTP error: {e}",
                context={"status_code": e.response.status_code},
            ) from e
        except Exception as e:
            self._circuit.record_failure(e)
            raise SourceUnavailableError(
                f"Polymarket error: {e}",
                context={"exception_type": type(e).__name__},
            ) from e

    def fetch_markets(self, limit: int = 100) -> list[dict[str, Any]]:
        """Fetch markets from Gamma (if supported) or CLOB."""
        if not self._circuit.is_available():
            raise SourceUnavailableError(
                "Polymarket circuit breaker is open",
                context={"circuit_state": self._circuit.state.value},
            )
        try:
            url = f"{self._base_url}/markets"
            response = self._client.get(url, params={"limit": limit})
            response.raise_for_status()
            self._circuit.record_success()
            data = response.json()
            return data if isinstance(data, list) else []
        except Exception as e:
            self._circuit.record_failure(e)
            raise SourceUnavailableError(f"Polymarket error: {e}") from e

    def search_events(self, query: str, limit: int = 20) -> list[dict[str, Any]]:
        """
        Search events by keyword (client-side filter on top of fetch_events).
        """
        try:
            events = self.fetch_events(limit=min(200, limit * 10), active=True)
            query_lower = query.lower()
            filtered = [
                e
                for e in events
                if query_lower in (e.get("title") or "").lower()
                or query_lower in (e.get("description") or "").lower()
            ]
            return filtered[:limit]
        except SourceUnavailableError:
            raise
        except Exception as e:
            raise SourceUnavailableError(f"Search error: {e}") from e

    def get_logistics_events(self, limit: int = 20) -> list[dict[str, Any]]:
        """Return events relevant to logistics/supply chain (client-side filter)."""
        keywords = [
            "shipping",
            "ship",
            "port",
            "trade",
            "tariff",
            "red sea",
            "suez",
            "panama",
            "taiwan",
            "china",
            "sanction",
            "embargo",
            "strike",
            "oil",
            "freight",
        ]
        all_events = self.fetch_events(limit=200, active=True)
        relevant = []
        for event in all_events:
            title = (event.get("title") or "").lower()
            desc = (event.get("description") or "").lower()
            text = f"{title} {desc}"
            if any(kw in text for kw in keywords):
                relevant.append(event)
        return relevant[:limit]

    def close(self) -> None:
        """Close the HTTP client."""
        self._client.close()
