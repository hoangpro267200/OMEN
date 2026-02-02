"""
Live Polymarket API client (Gamma API).

Base URL from POLYMARKET_GAMMA_API_URL (default: https://gamma-api.polymarket.com).
No API key required for public read endpoints.
"""

import re
import time
from typing import Any

import httpx

from omen.domain.errors import SourceRateLimitedError, SourceUnavailableError
from omen.infrastructure.retry import create_source_circuit_breaker
from omen.polymarket_settings import get_polymarket_settings
from omen.adapters.inbound.polymarket.http_retry import run_with_retry


def _log_source_failure(source_name: str, start: float, error_message: str) -> None:
    """Log source fetch failure and update metrics (best-effort)."""
    try:
        latency_ms = (time.perf_counter() - start) * 1000
        from omen.infrastructure.activity.activity_logger import get_activity_logger
        from omen.infrastructure.metrics.pipeline_metrics import get_metrics_collector
        get_activity_logger().log_source_fetch(
            source_name=source_name,
            events_count=0,
            latency_ms=latency_ms,
            success=False,
            error_message=error_message,
        )
        get_metrics_collector().update_source_health(
            source_name="polymarket",
            status="disconnected",
            events_fetched=0,
            latency_ms=latency_ms,
            error=True,
        )
    except Exception:
        pass


class PolymarketLiveClient:
    """
    Client for Polymarket Gamma API (live event/market data).

    URL and timeouts from POLYMARKET_* env. Uses trust_env for proxy (HTTP_PROXY/HTTPS_PROXY).
    """

    def __init__(
        self,
        timeout: float | None = None,
        use_gamma: bool = True,
        gamma_url: str | None = None,
        clob_url: str | None = None,
    ):
        s = get_polymarket_settings()
        self._timeout = timeout if timeout is not None else s.timeout_s
        self._gamma_url = (gamma_url or s.gamma_api_url).rstrip("/")
        self._clob_url = (clob_url or s.clob_api_url).rstrip("/")
        self._base_url = self._gamma_url if use_gamma else self._clob_url
        self._circuit = create_source_circuit_breaker("polymarket_live")
        self._client = httpx.Client(
            timeout=self._timeout,
            trust_env=s.httpx_trust_env,
            headers={"User-Agent": s.user_agent},
        )

    def fetch_events(
        self,
        limit: int = 50,
        active: bool = True,
        closed: bool = False,
    ) -> list[dict[str, Any]]:
        """
        Fetch events from Polymarket Gamma API.

        Returns list of event dicts with nested markets.
        Logs to activity and updates source health metrics.
        """
        if not self._circuit.is_available():
            raise SourceUnavailableError(
                "Polymarket circuit breaker is open",
                context={"circuit_state": self._circuit.state.value},
            )
        start = time.perf_counter()
        try:
            params: dict[str, Any] = {"limit": limit}
            if self._base_url == self._gamma_url:
                params["active"] = str(active).lower()
                params["closed"] = str(closed).lower()

            def _do_request() -> httpx.Response:
                return self._client.get(
                    f"{self._base_url}/events",
                    params=params,
                )

            response = run_with_retry(_do_request)
            response.raise_for_status()
            self._circuit.record_success()
            data = response.json()
            out = data if isinstance(data, list) else []
            latency_ms = (time.perf_counter() - start) * 1000
            try:
                from omen.infrastructure.activity.activity_logger import get_activity_logger
                from omen.infrastructure.metrics.pipeline_metrics import get_metrics_collector
                get_activity_logger().log_source_fetch(
                    source_name="Polymarket",
                    events_count=len(out),
                    latency_ms=latency_ms,
                    success=True,
                )
                get_metrics_collector().update_source_health(
                    source_name="polymarket",
                    status="connected",
                    events_fetched=len(out),
                    latency_ms=latency_ms,
                    error=False,
                )
            except Exception:
                pass
            return out
        except SourceRateLimitedError:
            raise
        except httpx.HTTPStatusError as e:
            self._circuit.record_failure(e)
            _log_source_failure("Polymarket", start, str(e))
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
        except SourceUnavailableError:
            raise
        except Exception as e:
            self._circuit.record_failure(e)
            _log_source_failure("Polymarket", start, str(e))
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
            def _do_request() -> httpx.Response:
                return self._client.get(
                    f"{self._base_url}/markets",
                    params={"limit": limit},
                )
            response = run_with_retry(_do_request)
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
        """Return events relevant to logistics/supply chain. Uses whole-word match so 'port'≠'sport', 'strike'≠'striker'."""
        keywords = [
            "shipping", "ship", "port", "trade", "tariff", "red sea", "suez",
            "panama", "taiwan", "china", "sanction", "embargo", "strike", "oil", "freight",
        ]
        fetch_limit = max(limit, 200, min(limit * 3, 2000))
        all_events = self.fetch_events(limit=fetch_limit, active=True)
        relevant = []
        for event in all_events:
            title = (event.get("title") or "").lower()
            desc = (event.get("description") or "").lower()
            text = f"{title} {desc}"
            if any(re.search(r"\b" + re.escape(kw) + r"\b", text) for kw in keywords):
                relevant.append(event)
        return relevant[:limit]

    def close(self) -> None:
        """Close the HTTP client."""
        self._client.close()
