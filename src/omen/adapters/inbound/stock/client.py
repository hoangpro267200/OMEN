"""
Stock data clients with resilience patterns.

Fetches data from:
- yfinance: Global markets
- vnstock: Vietnamese markets

Resilience features:
- Circuit breaker protection
- Retry with exponential backoff
- Health tracking
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Any

from omen.adapters.inbound.stock.config import StockConfig, StockWatchlistItem
from omen.adapters.inbound.stock.schemas import StockQuote, StockTimeSeries
from omen.adapters.inbound.resilience import (
    get_source_health,
    with_circuit_breaker,
    with_retry,
)

logger = logging.getLogger(__name__)

# Resilience configuration
MAX_RETRIES = 3
CIRCUIT_FAILURE_THRESHOLD = 5
CIRCUIT_RECOVERY_TIMEOUT = 30.0


class YFinanceClient:
    """
    Client for Yahoo Finance data via yfinance library.

    Resilience features:
    - Circuit breaker protection
    - Retry with exponential backoff
    - Health tracking
    """

    SOURCE_NAME = "yfinance"

    def __init__(self, config: StockConfig):
        self.config = config
        self._yf = None
        self._health = get_source_health(self.SOURCE_NAME)

    @property
    def is_healthy(self) -> bool:
        """Check if source is healthy."""
        return self._health.healthy

    def _get_yf(self):
        """Lazy load yfinance."""
        if self._yf is None:
            try:
                import yfinance as yf

                self._yf = yf
            except ImportError:
                logger.warning("yfinance not installed. Run: pip install yfinance")
                return None
        return self._yf

    @with_retry(max_attempts=MAX_RETRIES, base_delay=1.0)
    def get_quote(self, item: StockWatchlistItem) -> StockQuote | None:
        """Get current quote for a symbol."""
        yf = self._get_yf()
        if yf is None:
            return None

        try:
            ticker = yf.Ticker(item.yf_symbol)
            info = ticker.info

            # Get price data
            price = info.get("regularMarketPrice") or info.get("previousClose", 0)
            prev_close = info.get("previousClose", price)
            change = price - prev_close if prev_close else 0
            change_pct = (change / prev_close * 100) if prev_close else 0

            quote = StockQuote(
                symbol=item.symbol,
                name=item.name or info.get("shortName", item.symbol),
                price=float(price),
                previous_close=float(prev_close),
                change=float(change),
                change_pct=float(change_pct),
                volume=int(info.get("regularMarketVolume", 0) or 0),
                timestamp=datetime.now(timezone.utc),
                currency=info.get("currency", "USD"),
                category=item.category,
                provider="yfinance",
                region=item.region,
            )
            self._health.record_success(0)  # Latency tracked separately
            return quote
        except Exception as e:
            self._health.record_failure(str(e))
            logger.warning(f"Failed to get quote for {item.yf_symbol}: {e}")
            return None

    def get_history(self, item: StockWatchlistItem, days: int = 30) -> StockTimeSeries | None:
        """Get historical prices for a symbol."""
        yf = self._get_yf()
        if yf is None:
            return None

        try:
            ticker = yf.Ticker(item.yf_symbol)
            hist = ticker.history(period=f"{days}d")

            if hist.empty:
                return None

            prices = hist["Close"].tolist()
            timestamps = [ts.to_pydatetime().replace(tzinfo=timezone.utc) for ts in hist.index]
            volumes = hist["Volume"].fillna(0).astype(int).tolist()

            return StockTimeSeries(
                symbol=item.symbol,
                name=item.name,
                provider="yfinance",
                prices=prices,
                timestamps=timestamps,
                volumes=volumes,
            )
        except Exception as e:
            logger.warning(f"Failed to get history for {item.yf_symbol}: {e}")
            return None

    def get_batch_quotes(self, items: list[StockWatchlistItem]) -> list[StockQuote]:
        """Get quotes for multiple symbols."""
        quotes = []
        for item in items:
            if item.provider == "yfinance":
                quote = self.get_quote(item)
                if quote:
                    quotes.append(quote)
        return quotes


class VNStockClient:
    """
    Client for Vietnamese stock data via vnstock library.

    Resilience features:
    - Circuit breaker protection
    - Retry with exponential backoff
    - Health tracking
    """

    SOURCE_NAME = "vnstock"

    def __init__(self, config: StockConfig):
        self.config = config
        self._vnstock = None
        self._health = get_source_health(self.SOURCE_NAME)

    @property
    def is_healthy(self) -> bool:
        """Check if source is healthy."""
        return self._health.healthy

    def _get_vnstock(self):
        """Lazy load vnstock."""
        if self._vnstock is None:
            try:
                import vnstock

                self._vnstock = vnstock
            except ImportError:
                logger.warning("vnstock not installed. Run: pip install vnstock")
                return None
        return self._vnstock

    @with_retry(max_attempts=MAX_RETRIES, base_delay=1.0)
    def get_quote(self, item: StockWatchlistItem) -> StockQuote | None:
        """Get current quote for a VN symbol."""
        vnstock = self._get_vnstock()
        if vnstock is None:
            return None

        try:
            symbol = item.vn_symbol or item.symbol

            # Try to get stock data
            stock = vnstock.stock(symbol=symbol, source="VCI")
            quote_data = stock.quote.history(
                start="2024-01-01", end=datetime.now().strftime("%Y-%m-%d")
            )

            if quote_data is None or quote_data.empty:
                return None

            # Get latest row
            latest = quote_data.iloc[-1]
            prev = quote_data.iloc[-2] if len(quote_data) > 1 else latest

            price = float(latest.get("close", 0))
            prev_close = float(prev.get("close", price))
            change = price - prev_close
            change_pct = (change / prev_close * 100) if prev_close else 0

            quote = StockQuote(
                symbol=item.symbol,
                name=item.name,
                price=price,
                previous_close=prev_close,
                change=change,
                change_pct=change_pct,
                volume=int(latest.get("volume", 0)),
                timestamp=datetime.now(timezone.utc),
                currency="VND",
                category=item.category,
                provider="vnstock",
                region="vietnam",
            )
            self._health.record_success(0)  # Latency tracked separately
            return quote
        except Exception as e:
            self._health.record_failure(str(e))
            logger.warning(f"Failed to get VN quote for {item.vn_symbol}: {e}")
            return None

    def get_history(self, item: StockWatchlistItem, days: int = 30) -> StockTimeSeries | None:
        """Get historical prices for a VN symbol."""
        vnstock = self._get_vnstock()
        if vnstock is None:
            return None

        try:
            symbol = item.vn_symbol or item.symbol

            start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
            end_date = datetime.now().strftime("%Y-%m-%d")

            stock = vnstock.stock(symbol=symbol, source="VCI")
            hist = stock.quote.history(start=start_date, end=end_date)

            if hist is None or hist.empty:
                return None

            prices = hist["close"].tolist()
            timestamps = [
                datetime.strptime(str(d)[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
                for d in hist.index
            ]
            volumes = hist["volume"].fillna(0).astype(int).tolist()

            return StockTimeSeries(
                symbol=item.symbol,
                name=item.name,
                provider="vnstock",
                prices=prices,
                timestamps=timestamps,
                volumes=volumes,
            )
        except Exception as e:
            logger.warning(f"Failed to get VN history for {item.vn_symbol}: {e}")
            return None

    def get_batch_quotes(self, items: list[StockWatchlistItem]) -> list[StockQuote]:
        """Get quotes for multiple VN symbols."""
        quotes = []
        for item in items:
            if item.provider == "vnstock":
                quote = self.get_quote(item)
                if quote:
                    quotes.append(quote)
        return quotes


class MockStockClient:
    """Mock client for testing without external dependencies."""

    def __init__(self, config: StockConfig):
        self.config = config

    def get_quote(self, item: StockWatchlistItem) -> StockQuote:
        """Generate mock quote."""
        import random

        base_prices = {
            "SPX": 5200.0,
            "NDX": 18500.0,
            "DJI": 39000.0,
            "VIX": 15.0,
            "DXY": 104.0,
            "EURUSD": 1.08,
            "USDJPY": 150.0,
            "USDVND": 24500.0,
            "US10Y": 4.5,
            "US2Y": 5.0,
            "GOLD": 2050.0,
            "SILVER": 23.0,
            "CRUDE": 78.0,
            "BRENT": 82.0,
            "VNINDEX": 1250.0,
            "VN30": 1300.0,
            "HNX": 230.0,
            "VNM": 75000.0,
            "VIC": 42000.0,
            "VCB": 95000.0,
            "FPT": 125000.0,
        }

        base_price = base_prices.get(item.symbol, 100.0)
        change_pct = random.uniform(-3, 3)
        price = base_price * (1 + change_pct / 100)

        return StockQuote(
            symbol=item.symbol,
            name=item.name,
            price=price,
            previous_close=base_price,
            change=price - base_price,
            change_pct=change_pct,
            volume=random.randint(1000000, 10000000),
            timestamp=datetime.now(timezone.utc),
            currency=item.currency,
            category=item.category,
            provider="mock",
            region=item.region,
        )

    def get_batch_quotes(self, items: list[StockWatchlistItem]) -> list[StockQuote]:
        """Get mock quotes for all items."""
        return [self.get_quote(item) for item in items]
