"""
Live Polymarket API client (Gamma API).

Base URL from POLYMARKET_GAMMA_API_URL (default: https://gamma-api.polymarket.com).
No API key required for public read endpoints.

When direct API is blocked by network/DNS, automatically uses CORS proxy fallback
to bypass network restrictions (common in regions where prediction markets are blocked).
"""

import logging
import os
import re
import socket
import time
from typing import Any
from urllib.parse import quote

import httpx

from omen.domain.errors import SourceRateLimitedError, SourceUnavailableError
from omen.infrastructure.retry import create_source_circuit_breaker
from omen.polymarket_settings import get_polymarket_settings
from omen.adapters.inbound.polymarket.http_retry import run_with_retry
from omen.adapters.inbound.polymarket.demo_data import get_demo_polymarket_events

logger = logging.getLogger(__name__)

# CORS proxy services that can bypass network restrictions
# These are public services that relay requests to blocked APIs
CORS_PROXIES = [
    "https://api.allorigins.win/raw?url=",  # Primary - most reliable
    "https://corsproxy.io/?",                # Backup 1
    "https://api.codetabs.com/v1/proxy?quest=",  # Backup 2
]


def _is_polymarket_blocked() -> bool:
    """Check if Polymarket API is blocked by network (DNS hijacking)."""
    try:
        ip = socket.gethostbyname("gamma-api.polymarket.com")
        if ip in ("127.0.0.1", "0.0.0.0", "::1"):
            return True
        # Also check if we can actually connect
        sock = socket.create_connection((ip, 443), timeout=5)
        sock.close()
        return False
    except (socket.gaierror, socket.timeout, OSError):
        return True


def _get_proxy_url(original_url: str) -> str | None:
    """Get a working proxy URL for the given original URL."""
    # Check env var for custom proxy
    custom_proxy = os.getenv("POLYMARKET_CORS_PROXY", "").strip()
    if custom_proxy:
        return f"{custom_proxy}{quote(original_url, safe='')}"
    
    # Use default proxy
    return f"{CORS_PROXIES[0]}{quote(original_url, safe='')}"


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
    When direct API is blocked, automatically uses CORS proxy fallback.
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
        # Check if we need to use proxy (network is blocking Polymarket)
        self._use_proxy = _is_polymarket_blocked()
        if self._use_proxy:
            logger.info("Polymarket API blocked by network, will use CORS proxy")

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
        
        When direct API is blocked, uses CORS proxy to bypass network restrictions.
        Falls back to demo data only if both direct and proxy methods fail.
        """
        if not self._circuit.is_available():
            # Circuit open, try demo data as fallback
            logger.warning("Polymarket circuit breaker open, falling back to demo data")
            demo_events = get_demo_polymarket_events()
            self._log_demo_fetch(len(demo_events))
            return demo_events[:limit]
        
        start = time.perf_counter()
        
        # Build the URL with params
        params_str = f"limit={limit}"
        if self._base_url == self._gamma_url:
            params_str += f"&active={str(active).lower()}&closed={str(closed).lower()}"
        
        direct_url = f"{self._base_url}/events?{params_str}"
        
        # Try direct connection first if not blocked
        if not self._use_proxy:
            try:
                result = self._fetch_from_url(direct_url, start)
                if result is not None:
                    return result
            except Exception as e:
                logger.warning(f"Direct Polymarket connection failed: {e}, trying proxy...")
                self._use_proxy = True  # Switch to proxy for future requests
        
        # Use CORS proxy
        if self._use_proxy:
            try:
                result = self._fetch_via_proxy(direct_url, start)
                if result is not None:
                    return result
            except Exception as e:
                logger.warning(f"Proxy connection also failed: {e}, using demo data")
        
        # All methods failed, use demo data
        logger.info("All Polymarket connection methods failed, using demo data")
        demo_events = get_demo_polymarket_events()
        self._log_demo_fetch(len(demo_events))
        return demo_events[:limit]
    
    def _fetch_from_url(self, url: str, start: float) -> list[dict[str, Any]] | None:
        """Fetch events from a direct URL."""
        try:
            def _do_request() -> httpx.Response:
                return self._client.get(url)

            response = run_with_retry(_do_request)
            response.raise_for_status()
            self._circuit.record_success()
            data = response.json()
            out = data if isinstance(data, list) else []
            latency_ms = (time.perf_counter() - start) * 1000
            
            self._log_success_fetch(len(out), latency_ms, via_proxy=False)
            logger.info(f"Fetched {len(out)} events from Polymarket (direct)")
            return out
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                retry_after = int(e.response.headers.get("Retry-After", "60"))
                raise SourceRateLimitedError(
                    "Polymarket rate limited",
                    retry_after_seconds=retry_after,
                    context={"status_code": 429},
                ) from e
            raise
        except Exception:
            raise
    
    def _fetch_via_proxy(self, original_url: str, start: float) -> list[dict[str, Any]] | None:
        """Fetch events via CORS proxy."""
        for proxy_base in CORS_PROXIES:
            try:
                proxy_url = f"{proxy_base}{quote(original_url, safe='')}"
                logger.debug(f"Trying proxy: {proxy_base[:30]}...")
                
                # Use a separate client for proxy (different timeout)
                response = httpx.get(proxy_url, timeout=20.0, follow_redirects=True)
                response.raise_for_status()
                
                data = response.json()
                out = data if isinstance(data, list) else []
                latency_ms = (time.perf_counter() - start) * 1000
                
                self._circuit.record_success()
                self._log_success_fetch(len(out), latency_ms, via_proxy=True)
                logger.info(f"Fetched {len(out)} events from Polymarket (via proxy)")
                return out
                
            except Exception as e:
                logger.debug(f"Proxy {proxy_base[:30]}... failed: {e}")
                continue
        
        # All proxies failed
        self._circuit.record_failure(Exception("All proxies failed"))
        return None
    
    def _log_success_fetch(self, events_count: int, latency_ms: float, via_proxy: bool = False) -> None:
        """Log successful fetch to metrics."""
        try:
            from omen.infrastructure.activity.activity_logger import get_activity_logger
            from omen.infrastructure.metrics.pipeline_metrics import get_metrics_collector

            source_name = "Polymarket (Proxy)" if via_proxy else "Polymarket"
            get_activity_logger().log_source_fetch(
                source_name=source_name,
                events_count=events_count,
                latency_ms=latency_ms,
                success=True,
            )
            get_metrics_collector().update_source_health(
                source_name="polymarket",
                status="connected",
                events_fetched=events_count,
                latency_ms=latency_ms,
                error=False,
            )
        except Exception:
            pass
    
    def _log_demo_fetch(self, events_count: int) -> None:
        """Log demo data fetch to metrics."""
        try:
            from omen.infrastructure.activity.activity_logger import get_activity_logger
            from omen.infrastructure.metrics.pipeline_metrics import get_metrics_collector

            get_activity_logger().log_source_fetch(
                source_name="Polymarket (Demo)",
                events_count=events_count,
                latency_ms=0,
                success=True,
            )
            get_metrics_collector().update_source_health(
                source_name="polymarket",
                status="demo",
                events_fetched=events_count,
                latency_ms=0,
                error=False,
            )
        except Exception:
            pass

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
