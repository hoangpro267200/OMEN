"""Signal Source Port.

Defines the interface for ingesting raw market data.
Adapters implement this to connect to specific markets (Polymarket, Kalshi, etc.)
"""

from abc import ABC, abstractmethod
from typing import AsyncIterator, Iterator

from ...domain.models.raw_signal import RawSignalEvent


class SignalSource(ABC):
    """
    Abstract interface for signal sources.

    OMEN is market-agnostic. This interface allows plugging in
    any prediction market without changing core logic.
    """

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Identifier for this source (e.g., 'polymarket')."""
        ...

    @abstractmethod
    def fetch_events(self, limit: int = 100) -> Iterator[RawSignalEvent]:
        """
        Fetch events from the source.

        Args:
            limit: Maximum number of events to fetch

        Yields:
            Normalized RawSignalEvent objects
        """
        ...

    @abstractmethod
    async def fetch_events_async(self, limit: int = 100) -> AsyncIterator[RawSignalEvent]:
        """Async version of fetch_events."""
        ...

    @abstractmethod
    def fetch_by_id(self, market_id: str) -> RawSignalEvent | None:
        """Fetch a specific event by market ID."""
        ...


class SignalSourceError(Exception):
    """Raised when a signal source encounters an error."""

    pass
