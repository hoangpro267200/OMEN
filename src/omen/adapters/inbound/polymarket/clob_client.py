"""
Polymarket CLOB API client for real-time market data.

Base URL from POLYMARKET_CLOB_API_URL (default: https://clob.polymarket.com).
Docs: https://docs.polymarket.com
"""

from dataclasses import dataclass
from datetime import datetime, timezone
import logging
from typing import Any

import httpx

from omen.domain.errors import SourceUnavailableError
from omen.infrastructure.retry import CircuitBreaker
from omen.polymarket_settings import get_polymarket_settings
from omen.adapters.inbound.polymarket.http_retry import run_with_retry

logger = logging.getLogger(__name__)


@dataclass
class CLOBPrice:
    """Real-time price data from CLOB."""

    token_id: str
    best_bid: float
    best_ask: float
    mid_price: float
    spread: float
    last_trade_price: float | None
    timestamp: datetime


@dataclass
class OrderbookLevel:
    """Single level in orderbook."""

    price: float
    size: float


@dataclass
class Orderbook:
    """Full orderbook for a market."""

    token_id: str
    bids: list[OrderbookLevel]
    asks: list[OrderbookLevel]
    spread: float
    mid_price: float
    total_bid_liquidity: float
    total_ask_liquidity: float


class PolymarketCLOBClient:
    """
    Client for Polymarket CLOB API.

    URL and timeouts from POLYMARKET_* env. Uses trust_env for proxy.
    """

    def __init__(self, timeout: float | int | None = None, clob_url: str | None = None):
        s = get_polymarket_settings()
        self._base_url = (clob_url or s.clob_api_url).rstrip("/")
        self._timeout = timeout if timeout is not None else s.timeout_s
        self._circuit = CircuitBreaker(name="polymarket-clob", failure_threshold=5)
        self._client = httpx.Client(
            timeout=self._timeout,
            trust_env=s.httpx_trust_env,
            headers={"User-Agent": s.user_agent},
        )

    def get_price(self, token_id: str) -> CLOBPrice:
        """
        Get current price for a specific market token.

        Uses Polymarket /price with side=BUY and side=SELL to derive bid/ask.
        """
        if not self._circuit.is_available():
            raise SourceUnavailableError("CLOB circuit breaker open")

        try:
            def do_ask() -> httpx.Response:
                return self._client.get(
                    f"{self._base_url}/price",
                    params={"token_id": token_id, "side": "BUY"},
                )
            def do_bid() -> httpx.Response:
                return self._client.get(
                    f"{self._base_url}/price",
                    params={"token_id": token_id, "side": "SELL"},
                )
            ask_resp = run_with_retry(do_ask)
            bid_resp = run_with_retry(do_bid)
            ask_resp.raise_for_status()
            bid_resp.raise_for_status()

            adata = ask_resp.json()
            bdata = bid_resp.json()
            best_ask = float(adata.get("price", 1))
            best_bid = float(bdata.get("price", 0))

            self._circuit.record_success()

            return CLOBPrice(
                token_id=token_id,
                best_bid=best_bid,
                best_ask=best_ask,
                mid_price=(best_bid + best_ask) / 2,
                spread=best_ask - best_bid,
                last_trade_price=None,
                timestamp=datetime.now(timezone.utc),
            )

        except httpx.TimeoutException as e:
            self._circuit.record_failure(e)
            raise SourceUnavailableError("CLOB API timeout") from e
        except Exception as e:
            self._circuit.record_failure(e)
            raise SourceUnavailableError(f"CLOB API error: {e}") from e

    def get_prices_bulk(self, token_ids: list[str]) -> dict[str, CLOBPrice]:
        """Get prices for multiple tokens efficiently."""
        results: dict[str, CLOBPrice] = {}
        for token_id in token_ids:
            try:
                results[token_id] = self.get_price(token_id)
            except SourceUnavailableError:
                continue
        return results

    def get_orderbook(self, token_id: str) -> Orderbook:
        """Get full orderbook for a market."""
        if not self._circuit.is_available():
            raise SourceUnavailableError("CLOB circuit breaker open")

        try:
            def do_request() -> httpx.Response:
                return self._client.get(
                    f"{self._base_url}/book",
                    params={"token_id": token_id},
                )
            response = run_with_retry(do_request)
            response.raise_for_status()
            data: dict[str, Any] = response.json()

            self._circuit.record_success()

            bids = [
                OrderbookLevel(price=float(b["price"]), size=float(b["size"]))
                for b in data.get("bids", [])
            ]
            asks = [
                OrderbookLevel(price=float(a["price"]), size=float(a["size"]))
                for a in data.get("asks", [])
            ]

            best_bid = bids[0].price if bids else 0.0
            best_ask = asks[0].price if asks else 1.0

            return Orderbook(
                token_id=token_id,
                bids=bids,
                asks=asks,
                spread=best_ask - best_bid,
                mid_price=(best_bid + best_ask) / 2,
                total_bid_liquidity=sum(b.size for b in bids),
                total_ask_liquidity=sum(a.size for a in asks),
            )

        except Exception as e:
            self._circuit.record_failure(e)
            raise SourceUnavailableError(f"CLOB orderbook error: {e}") from e

    def get_midpoint(self, token_id: str) -> float:
        """Get just the midpoint price (fastest)."""
        try:
            def do_request() -> httpx.Response:
                return self._client.get(
                    f"{self._base_url}/midpoint",
                    params={"token_id": token_id},
                )
            response = run_with_retry(do_request)
            response.raise_for_status()
            data = response.json()
            mid = data.get("mid") or data.get("midpoint") or data.get("price")
            return float(mid) if mid is not None else 0.5
        except Exception:
            return 0.5
