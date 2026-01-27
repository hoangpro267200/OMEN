"""Async in-memory signal repository for testing and development."""

import asyncio
from collections import OrderedDict
from datetime import datetime

from omen.application.ports.signal_repository import AsyncSignalRepository
from omen.domain.models.omen_signal import OmenSignal


class AsyncInMemorySignalRepository(AsyncSignalRepository):
    """
    Async in-memory repository.

    Thread-safe via asyncio lock. Supports bounded size with FIFO eviction.
    """

    def __init__(self, max_size: int = 10000) -> None:
        self._signals: OrderedDict[str, OmenSignal] = OrderedDict()
        self._hash_index: dict[str, str] = {}
        self._max_size = max_size
        self._lock = asyncio.Lock()

    async def save_async(self, signal: OmenSignal) -> None:
        async with self._lock:
            while len(self._signals) >= self._max_size:
                _oldest_id, oldest = self._signals.popitem(last=False)
                self._hash_index.pop(oldest.input_event_hash, None)
            self._signals[signal.signal_id] = signal
            self._hash_index[signal.input_event_hash] = signal.signal_id

    async def find_by_id_async(self, signal_id: str) -> OmenSignal | None:
        async with self._lock:
            return self._signals.get(signal_id)

    async def find_by_hash_async(self, input_event_hash: str) -> OmenSignal | None:
        async with self._lock:
            signal_id = self._hash_index.get(input_event_hash)
            if signal_id is not None:
                return self._signals.get(signal_id)
            return None

    async def find_recent_async(
        self,
        limit: int = 100,
        since: datetime | None = None,
    ) -> list[OmenSignal]:
        async with self._lock:
            signals = list(reversed(self._signals.values()))
            if since is not None:
                signals = [s for s in signals if s.generated_at >= since]
            return signals[:limit]
