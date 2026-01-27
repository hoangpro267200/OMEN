"""
Enhanced Polymarket source combining Gamma + CLOB APIs.
"""

from datetime import datetime
from typing import Iterator

from omen.adapters.inbound.polymarket.clob_client import CLOBPrice, PolymarketCLOBClient
from omen.adapters.inbound.polymarket.live_client import PolymarketLiveClient
from omen.adapters.inbound.polymarket.mapper import PolymarketMapper
from omen.domain.models.raw_signal import RawSignalEvent


class EnhancedPolymarketSource:
    """
    Signal source that combines:
    - Gamma API: Event metadata, categories, descriptions
    - CLOB API: Real-time prices, orderbook liquidity

    This gives more accurate probability and better liquidity assessment.
    """

    def __init__(
        self,
        gamma_client: PolymarketLiveClient | None = None,
        clob_client: PolymarketCLOBClient | None = None,
        mapper: PolymarketMapper | None = None,
        logistics_only: bool = True,
    ) -> None:
        self._gamma = gamma_client or PolymarketLiveClient()
        self._clob = clob_client or PolymarketCLOBClient()
        self._mapper = mapper or PolymarketMapper()
        self._logistics_only = logistics_only

    def fetch_events_enhanced(self, limit: int = 50) -> Iterator[RawSignalEvent]:
        """
        Fetch events with enhanced price data from CLOB.

        Flow:
        1. Get events from Gamma API
        2. For each market, get real-time price from CLOB
        3. Enrich RawSignalEvent with CLOB data
        """
        if self._logistics_only:
            events = self._gamma.get_logistics_events(limit=limit)
        else:
            events = self._gamma.fetch_events(limit=limit)

        for event in events:
            signals = self._mapper.map_event(event)

            for signal in signals:
                try:
                    token_id = self._get_token_id(signal, event)

                    if token_id:
                        clob_price = self._clob.get_price(token_id)
                        signal = self._enrich_with_clob(signal, clob_price)

                except Exception:
                    # CLOB failed, use Gamma data as fallback
                    pass

                yield signal

    def _get_token_id(self, signal: RawSignalEvent, event: dict) -> str | None:
        """Extract token ID for CLOB lookup."""
        markets = event.get("markets") or [event]
        sid = str(signal.market.market_id)
        for market in markets:
            mid = market.get("id") or market.get("conditionId")
            if mid is not None and str(mid) == sid:
                tid = market.get("conditionId")
                if tid:
                    return str(tid)
                ids = market.get("clobTokenIds") or []
                if isinstance(ids, list) and ids:
                    return str(ids[0])
                break
        return None

    def _enrich_with_clob(
        self,
        signal: RawSignalEvent,
        clob: CLOBPrice,
    ) -> RawSignalEvent:
        """Enrich signal with CLOB price data."""
        base = signal.raw_payload or {}
        clob_data = {
            "best_bid": clob.best_bid,
            "best_ask": clob.best_ask,
            "spread": clob.spread,
            "last_trade": clob.last_trade_price,
            "timestamp": clob.timestamp.isoformat(),
        }
        return signal.model_copy(
            update={
                "probability": max(0.0, min(1.0, clob.mid_price)),
                "raw_payload": {**base, "clob_data": clob_data},
            }
        )
