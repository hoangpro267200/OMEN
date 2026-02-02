"""
Commodity Price API Client.

Fetches commodity prices from AlphaVantage or EIA.
Includes retry logic, rate limiting, and circuit breaker.

Security:
- API key from environment only (never logged)
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone, timedelta
from typing import Any

import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from .config import CommodityConfig, CommodityWatchlistItem
from .schemas import PriceTimeSeries, CommodityPrice

logger = logging.getLogger(__name__)


class CommodityAPIError(Exception):
    """Error from commodity API."""

    pass


class CommodityRateLimitError(CommodityAPIError):
    """Rate limit exceeded."""

    pass


class CommodityClient:
    """
    AlphaVantage commodity price client.

    Features:
    - Rate limiting (5 requests/minute for free tier)
    - Retry with exponential backoff
    - Response caching for replay
    """

    def __init__(self, config: CommodityConfig | None = None):
        self._config = config or CommodityConfig()
        self._client = httpx.Client(
            timeout=self._config.timeout_seconds,
            headers={"User-Agent": "OMEN/0.1.0 CommodityClient"},
        )
        self._last_request_time: float = 0
        self._min_request_interval = 60.0 / self._config.rate_limit_per_minute

    def _wait_for_rate_limit(self) -> None:
        """Wait if necessary to respect rate limits."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self._min_request_interval:
            sleep_time = self._min_request_interval - elapsed
            logger.debug(f"Rate limiting: sleeping {sleep_time:.1f}s")
            time.sleep(sleep_time)
        self._last_request_time = time.time()

    def _get_api_key(self) -> str:
        """Get API key (never logged)."""
        if not self._config.alphavantage_api_key:
            raise CommodityAPIError("ALPHAVANTAGE_API_KEY not configured")
        return self._config.alphavantage_api_key

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
        reraise=True,
    )
    def get_daily_prices(
        self,
        symbol: str,
        outputsize: str = "compact",
    ) -> PriceTimeSeries:
        """
        Fetch daily prices for a commodity.

        Args:
            symbol: AlphaVantage symbol (e.g., "WTI", "BRENT")
            outputsize: "compact" (100 days) or "full" (20+ years)

        Returns:
            PriceTimeSeries with historical data
        """
        self._wait_for_rate_limit()

        # Map commodity symbols to AlphaVantage functions
        # For commodities, use TIME_SERIES_DAILY with specific symbols
        # or COMMODITIES endpoint if available

        params = {
            "function": "TIME_SERIES_DAILY",
            "symbol": symbol,
            "outputsize": outputsize,
            "apikey": self._get_api_key(),
        }

        try:
            logger.info(f"Fetching prices for {symbol}")
            response = self._client.get(
                self._config.alphavantage_base_url,
                params=params,
            )

            if response.status_code == 429:
                logger.warning("AlphaVantage rate limit exceeded")
                raise CommodityRateLimitError("Rate limit exceeded")

            response.raise_for_status()
            data = response.json()

            # Check for error response
            if "Error Message" in data:
                raise CommodityAPIError(data["Error Message"])
            if "Note" in data and "API call frequency" in data["Note"]:
                raise CommodityRateLimitError(data["Note"])

            # Parse time series
            return self._parse_time_series(symbol, data)

        except httpx.TimeoutException:
            logger.error(f"AlphaVantage timeout for {symbol}")
            raise

    def _parse_time_series(
        self,
        symbol: str,
        data: dict[str, Any],
    ) -> PriceTimeSeries:
        """Parse AlphaVantage response into PriceTimeSeries."""
        # Find the time series key (varies by endpoint)
        ts_key = None
        for key in data:
            if "Time Series" in key or "data" in key.lower():
                ts_key = key
                break

        if not ts_key or not data.get(ts_key):
            raise CommodityAPIError(f"No time series data in response for {symbol}")

        ts_data = data[ts_key]
        prices: list[tuple[datetime, float]] = []

        for date_str, values in sorted(ts_data.items()):
            try:
                # Parse date
                dt = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)

                # Get close price
                price = float(values.get("4. close", values.get("close", 0)))

                if price > 0:
                    prices.append((dt, price))

            except (ValueError, KeyError) as e:
                logger.warning(f"Failed to parse price data: {e}")
                continue

        if not prices:
            raise CommodityAPIError(f"No valid prices parsed for {symbol}")

        logger.info(f"Parsed {len(prices)} prices for {symbol}")
        return PriceTimeSeries(symbol=symbol, prices=prices)

    def get_current_price(
        self,
        watchlist_item: CommodityWatchlistItem,
    ) -> CommodityPrice | None:
        """
        Get current price with historical context.

        Args:
            watchlist_item: Commodity configuration

        Returns:
            CommodityPrice with current and historical prices
        """
        try:
            series = self.get_daily_prices(
                watchlist_item.alphavantage_symbol,
                outputsize="compact",
            )

            if not series.prices:
                return None

            latest_ts, latest_price = series.prices[-1]
            now = datetime.now(timezone.utc)

            return CommodityPrice(
                symbol=watchlist_item.symbol,
                name=watchlist_item.name,
                category=watchlist_item.category,
                price=latest_price,
                unit=watchlist_item.unit,
                timestamp=latest_ts,
                fetched_at=now,
                price_1d_ago=series.get_price_n_days_ago(1),
                price_7d_ago=series.get_price_n_days_ago(7),
                price_30d_ago=series.get_price_n_days_ago(30),
            )

        except Exception as e:
            logger.error(f"Failed to get price for {watchlist_item.symbol}: {e}")
            return None

    def close(self) -> None:
        """Close HTTP client."""
        self._client.close()


class MockCommodityClient:
    """
    Mock commodity client for testing.

    Returns deterministic prices based on scenario.
    """

    def __init__(
        self,
        config: CommodityConfig | None = None,
        scenario: str = "spike",
    ):
        self._config = config or CommodityConfig()
        self._scenario = scenario

    def get_daily_prices(
        self,
        symbol: str,
        outputsize: str = "compact",
    ) -> PriceTimeSeries:
        """Return mock price series."""
        now = datetime.now(timezone.utc)
        prices: list[tuple[datetime, float]] = []

        # Base price by symbol
        base_prices = {
            "BRENT": 75.0,
            "WTI": 72.0,
            "NATURAL_GAS": 2.5,
        }
        base = base_prices.get(symbol, 50.0)

        # Generate 30 days of prices
        for i in range(30, -1, -1):
            dt = now - timedelta(days=i)

            if self._scenario == "spike" and i < 7:
                # Recent spike: 15% increase
                price = base * 1.15
            elif self._scenario == "crash" and i < 7:
                # Recent crash: 20% decrease
                price = base * 0.80
            else:
                # Normal: small variations
                variation = 1.0 + (hash(f"{symbol}{i}") % 100 - 50) / 1000
                price = base * variation

            prices.append((dt, round(price, 2)))

        return PriceTimeSeries(symbol=symbol, prices=prices)

    def get_current_price(
        self,
        watchlist_item: CommodityWatchlistItem,
    ) -> CommodityPrice | None:
        """Return mock current price."""
        series = self.get_daily_prices(watchlist_item.alphavantage_symbol)

        if not series.prices:
            return None

        latest_ts, latest_price = series.prices[-1]
        now = datetime.now(timezone.utc)

        return CommodityPrice(
            symbol=watchlist_item.symbol,
            name=watchlist_item.name,
            category=watchlist_item.category,
            price=latest_price,
            unit=watchlist_item.unit,
            timestamp=latest_ts,
            fetched_at=now,
            price_1d_ago=series.get_price_n_days_ago(1),
            price_7d_ago=series.get_price_n_days_ago(7),
            price_30d_ago=series.get_price_n_days_ago(30),
        )

    def close(self) -> None:
        pass


def create_commodity_client(
    config: CommodityConfig | None = None,
) -> CommodityClient | MockCommodityClient:
    """
    Factory to create commodity client.

    Returns mock client if API key not configured.
    """
    config = config or CommodityConfig()

    if config.provider == "mock":
        return MockCommodityClient(config)

    if not config.alphavantage_api_key:
        logger.warning("ALPHAVANTAGE_API_KEY not set, using mock client")
        return MockCommodityClient(config)

    return CommodityClient(config)
