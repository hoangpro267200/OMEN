"""
Live Polymarket signal source for OMEN pipeline.

Uses Gamma API via PolymarketLiveClient and maps responses to RawSignalEvent.
"""

from __future__ import annotations

import asyncio
from typing import AsyncIterator, Iterator

from omen.application.ports.signal_source import SignalSource
from omen.domain.models.raw_signal import RawSignalEvent

from .live_client import PolymarketLiveClient
from .mapper import PolymarketMapper


class PolymarketSignalSource(SignalSource):
    """
    Live signal source from Polymarket Gamma API.

    Fetches events/markets and maps them to RawSignalEvent for the OMEN pipeline.
    """

    def __init__(
        self,
        client: PolymarketLiveClient | None = None,
        mapper: PolymarketMapper | None = None,
        logistics_only: bool = True,
    ):
        self._client = client or PolymarketLiveClient()
        self._mapper = mapper or PolymarketMapper()
        self._logistics_only = logistics_only

    @property
    def source_name(self) -> str:
        return "polymarket"

    def fetch_events(self, limit: int = 100) -> Iterator[RawSignalEvent]:
        """Fetch events from Polymarket and yield RawSignalEvent(s)."""
        if self._logistics_only:
            events = self._client.get_logistics_events(limit=limit)
        else:
            events = self._client.fetch_events(limit=limit)
        for event in events:
            for signal in self._mapper.map_event(event):
                yield signal

    async def fetch_events_async(self, limit: int = 100) -> AsyncIterator[RawSignalEvent]:
        """Async version: run sync fetch in executor and return async iterator."""
        loop = asyncio.get_event_loop()
        if self._logistics_only:
            events = await loop.run_in_executor(
                None, lambda: self._client.get_logistics_events(limit=limit)
            )
        else:
            events = await loop.run_in_executor(
                None, lambda: self._client.fetch_events(limit=limit)
            )

        async def _gen() -> AsyncIterator[RawSignalEvent]:
            for event in events:
                for signal in self._mapper.map_event(event):
                    yield signal

        return _gen()

    def fetch_by_id(self, market_id: str) -> RawSignalEvent | None:
        """Fetch a single event/market by ID by scanning fetched events."""
        events = self._client.fetch_events(limit=200)
        for event in events:
            for signal in self._mapper.map_event(event):
                if str(signal.event_id) == market_id or market_id in str(signal.event_id):
                    return signal
                if str(signal.market.market_id) == market_id:
                    return signal
        return None

    def search(self, query: str, limit: int = 20) -> Iterator[RawSignalEvent]:
        """Search events by keyword and yield RawSignalEvent(s)."""
        events = self._client.search_events(query, limit=limit)
        for event in events:
            for signal in self._mapper.map_event(event):
                yield signal
