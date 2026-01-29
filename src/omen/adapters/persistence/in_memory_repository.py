"""In-memory signal repository."""

from typing import Dict
from datetime import datetime

from ...application.ports.signal_repository import SignalRepository
from ...domain.models.omen_signal import OmenSignal


class InMemorySignalRepository(SignalRepository):
    """In-memory implementation of SignalRepository."""

    def __init__(self):
        """Initialize in-memory repository."""
        self._signals_by_id: Dict[str, OmenSignal] = {}
        self._signals_by_hash: Dict[str, OmenSignal] = {}
        self._signals_by_event_id: Dict[str, list[OmenSignal]] = {}
        self._signals_list: list[OmenSignal] = []

    def save(self, signal: OmenSignal) -> None:
        """Persist an OMEN signal (pure contract)."""
        self._signals_by_id[signal.signal_id] = signal
        if getattr(signal, "input_event_hash", None) is not None:
            self._signals_by_hash[signal.input_event_hash] = signal
        event_key = signal.source_event_id
        if event_key not in self._signals_by_event_id:
            self._signals_by_event_id[event_key] = []
        self._signals_by_event_id[event_key].append(signal)
        
        # Update list (remove old if exists, add new)
        self._signals_list = [
            s for s in self._signals_list if s.signal_id != signal.signal_id
        ]
        self._signals_list.append(signal)
        # Sort by generated_at descending
        self._signals_list.sort(key=lambda s: s.generated_at, reverse=True)

    def find_by_id(self, signal_id: str) -> OmenSignal | None:
        """Find signal by its OMEN ID."""
        return self._signals_by_id.get(signal_id)

    def find_by_hash(self, input_event_hash: str) -> OmenSignal | None:
        """Find signal by input event hash."""
        return self._signals_by_hash.get(input_event_hash)

    def find_by_event_id(self, event_id: str) -> list[OmenSignal]:
        """Find all signals generated from a source event."""
        return self._signals_by_event_id.get(event_id, [])

    def find_recent(
        self,
        limit: int = 100,
        offset: int = 0,
        since: datetime | None = None,
    ) -> list[OmenSignal]:
        """Find recent signals with pagination."""
        signals = self._signals_list
        if since is not None:
            signals = [s for s in signals if s.generated_at >= since]
        return signals[offset : offset + limit]

    def count(self, since: datetime | None = None) -> int:
        """Count total signals, optionally only those after since."""
        if since is None:
            return len(self._signals_list)
        return sum(1 for s in self._signals_list if s.generated_at >= since)
