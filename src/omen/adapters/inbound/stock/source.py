"""
Stock SignalSource implementation.

Fetches stock/index/forex/bond data from yfinance and vnstock,
detects significant movements, and emits RawSignalEvents.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator, Iterator
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from omen.adapters.inbound.stock.client import MockStockClient, VNStockClient, YFinanceClient
from omen.adapters.inbound.stock.config import StockConfig
from omen.adapters.inbound.stock.mapper import StockMapper
from omen.adapters.inbound.stock.schemas import StockQuote
from omen.adapters.inbound.stock.spike_detector import SpikeDetector
from omen.application.ports.signal_source import SignalSource
from omen.domain.models.raw_signal import RawSignalEvent

logger = logging.getLogger(__name__)


class StockSignalSource(SignalSource):
    """
    Signal source for stock/index/forex/bond data.
    
    Supports:
    - yfinance: Global markets (SPX, NDX, VIX, DXY, US10Y, Gold, Oil, etc.)
    - vnstock: Vietnamese markets (VN-Index, VN30, HNX, VNM, VIC, etc.)
    - mock: Testing without external dependencies
    """
    
    def __init__(
        self,
        config: StockConfig | None = None,
        include_minor_moves: bool = False,
    ):
        self.config = config or StockConfig()
        self.include_minor_moves = include_minor_moves
        
        # Initialize clients based on provider setting
        self.yf_client = None
        self.vn_client = None
        self.mock_client = None
        
        if self.config.provider == "mock":
            self.mock_client = MockStockClient(self.config)
        else:
            if self.config.enable_yfinance and self.config.provider in ("yfinance", "both"):
                self.yf_client = YFinanceClient(self.config)
            if self.config.enable_vnstock and self.config.provider in ("vnstock", "both"):
                self.vn_client = VNStockClient(self.config)
        
        self.spike_detector = SpikeDetector(self.config)
        self.mapper = StockMapper(self.config)
    
    @property
    def source_name(self) -> str:
        return "stock"
    
    def fetch_events(self, limit: int = 100) -> Iterator[RawSignalEvent]:
        """Fetch stock events from all configured providers."""
        logger.info(f"Fetching stock events (limit={limit}, provider={self.config.provider})")
        
        watchlist = self.config.get_watchlist()
        events_emitted = 0
        
        for item in watchlist:
            if events_emitted >= limit:
                break
            
            try:
                quote = self._get_quote(item)
                if quote is None:
                    continue
                
                # Detect spike
                spike = self.spike_detector.detect_from_quote(quote, item)
                
                # Skip minor moves unless explicitly included
                if not self.include_minor_moves and spike is None:
                    if abs(quote.change_pct) < item.spike_threshold_pct:
                        continue
                
                # Map to event
                event = self.mapper.map_quote(quote, item, spike)
                if event:
                    yield event
                    events_emitted += 1
                    logger.debug(f"Emitted stock event: {quote.symbol} ({quote.change_pct:+.2f}%)")
                    
            except Exception as e:
                logger.warning(f"Error processing {item.symbol}: {e}")
                continue
        
        logger.info(f"Fetched {events_emitted} stock events")
    
    def _get_quote(self, item) -> StockQuote | None:
        """Get quote from appropriate client."""
        if self.mock_client:
            return self.mock_client.get_quote(item)
        
        if item.provider == "vnstock" and self.vn_client:
            return self.vn_client.get_quote(item)
        
        if item.provider == "yfinance" and self.yf_client:
            return self.yf_client.get_quote(item)
        
        # Fallback to yfinance for global items
        if self.yf_client:
            return self.yf_client.get_quote(item)
        
        return None
    
    def get_all_quotes(self) -> list[StockQuote]:
        """Get all quotes from watchlist (for dashboard display)."""
        quotes = []
        watchlist = self.config.get_watchlist()
        
        for item in watchlist:
            try:
                quote = self._get_quote(item)
                if quote:
                    quotes.append(quote)
            except Exception as e:
                logger.warning(f"Error getting quote for {item.symbol}: {e}")
        
        return quotes
    
    def get_global_quotes(self) -> list[StockQuote]:
        """Get only global market quotes."""
        quotes = []
        for item in self.config.get_global_watchlist():
            try:
                quote = self._get_quote(item)
                if quote:
                    quotes.append(quote)
            except Exception as e:
                logger.warning(f"Error getting global quote for {item.symbol}: {e}")
        return quotes
    
    def get_vn_quotes(self) -> list[StockQuote]:
        """Get only Vietnamese market quotes."""
        quotes = []
        for item in self.config.get_vn_watchlist():
            try:
                quote = self._get_quote(item)
                if quote:
                    quotes.append(quote)
            except Exception as e:
                logger.warning(f"Error getting VN quote for {item.symbol}: {e}")
        return quotes
    
    async def fetch_events_async(self, limit: int = 100) -> AsyncIterator[RawSignalEvent]:
        """Async version of fetch_events."""
        # For now, just wrap the sync version
        for event in self.fetch_events(limit=limit):
            yield event
    
    def fetch_by_id(self, market_id: str) -> RawSignalEvent | None:
        """Fetch a specific event by market ID (symbol)."""
        # Extract symbol from market_id (format: stock-<symbol>)
        symbol = market_id.replace("stock-", "").upper()
        
        watchlist = self.config.get_watchlist()
        for item in watchlist:
            if item.symbol.upper() == symbol:
                try:
                    quote = self._get_quote(item)
                    if quote:
                        spike = self.spike_detector.detect_from_quote(quote, item)
                        return self.mapper.map_quote(quote, item, spike)
                except Exception as e:
                    logger.warning(f"Error fetching {symbol}: {e}")
        
        return None


def create_stock_source(
    provider: str = "both",
    include_minor_moves: bool = False,
) -> StockSignalSource:
    """Factory function to create stock signal source."""
    config = StockConfig(provider=provider)
    return StockSignalSource(config=config, include_minor_moves=include_minor_moves)
