"""Signal Repository Port.

Defines interface for persisting and retrieving OMEN outputs.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Protocol, runtime_checkable

from ...domain.models.omen_signal import OmenSignal


@runtime_checkable
class AsyncSignalRepository(Protocol):
    """Async interface for signal persistence (high-throughput / async pipeline)."""

    async def save_async(self, signal: OmenSignal) -> None:
        """Persist an OMEN signal asynchronously."""
        ...

    async def find_by_id_async(self, signal_id: str) -> OmenSignal | None:
        """Find signal by its OMEN ID."""
        ...

    async def find_by_hash_async(self, input_event_hash: str) -> OmenSignal | None:
        """
        Find signal by input event hash (idempotency).
        """
        ...

    async def find_recent_async(
        self,
        limit: int = 100,
        since: datetime | None = None,
    ) -> list[OmenSignal]:
        """Find recent signals."""
        ...


class SignalRepository(ABC):
    """
    Abstract interface for signal persistence.

    Enables idempotency checking and historical queries.
    """

    @abstractmethod
    def save(self, signal: OmenSignal) -> None:
        """Persist an OMEN signal."""
        ...

    @abstractmethod
    def find_by_id(self, signal_id: str) -> OmenSignal | None:
        """Find signal by its OMEN ID."""
        ...

    @abstractmethod
    def find_by_hash(self, input_event_hash: str) -> OmenSignal | None:
        """
        Find signal by input event hash.

        Used for idempotency: if we've already processed this exact
        input, return the cached result.
        """
        ...

    @abstractmethod
    def find_by_event_id(self, event_id: str) -> list[OmenSignal]:
        """Find all signals generated from a source event."""
        ...

    @abstractmethod
    def find_recent(
        self,
        limit: int = 100,
        offset: int = 0,
        since: datetime | None = None,
    ) -> list[OmenSignal]:
        """
        Find recent signals with pagination.

        Args:
            limit: Maximum results to return.
            offset: Number of results to skip (for pagination).
            since: If set, only return signals with generated_at >= since.
        """
        ...

    @abstractmethod
    def count(self, since: datetime | None = None) -> int:
        """Count total signals, optionally only those after since."""
        ...
