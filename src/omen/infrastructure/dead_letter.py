"""
Dead Letter Queue for failed signals.

Stores failed events for later inspection and reprocessing.
"""

import logging
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from omen.domain.errors import OmenError
from omen.domain.models.raw_signal import RawSignalEvent

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DeadLetterEntry:
    """A failed event with error context."""

    event: RawSignalEvent
    error: OmenError
    failed_at: datetime
    retry_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": str(self.event.event_id),
            "event_hash": self.event.input_event_hash,
            "error": self.error.to_dict(),
            "failed_at": self.failed_at.isoformat(),
            "retry_count": self.retry_count,
        }


class DeadLetterQueue:
    """
    In-memory dead letter queue.

    For production, implement with Redis, Kafka, or a database.
    """

    def __init__(self, max_size: int = 10000):
        self._queue: deque[DeadLetterEntry] = deque(maxlen=max_size)
        self._max_size = max_size

    def add(
        self,
        event: RawSignalEvent,
        error: OmenError,
        retry_count: int = 0,
    ) -> DeadLetterEntry:
        """Add a failed event to the queue."""
        entry = DeadLetterEntry(
            event=event,
            error=error,
            failed_at=datetime.now(timezone.utc),
            retry_count=retry_count,
        )
        self._queue.append(entry)
        logger.warning(
            "Event %s added to DLQ: %s",
            event.event_id,
            error.message,
            extra={"dlq_entry": entry.to_dict()},
        )
        return entry

    def pop(self) -> DeadLetterEntry | None:
        """Remove and return the oldest entry."""
        try:
            return self._queue.popleft()
        except IndexError:
            return None

    def peek(self, n: int = 10) -> list[DeadLetterEntry]:
        """View the oldest n entries without removing."""
        return list(self._queue)[:n]

    def size(self) -> int:
        return len(self._queue)

    def is_empty(self) -> bool:
        return len(self._queue) == 0

    def clear(self) -> int:
        """Clear all entries, return count cleared."""
        count = len(self._queue)
        self._queue.clear()
        return count

    def get_by_event_id(self, event_id: str) -> DeadLetterEntry | None:
        """Find entry by event ID."""
        for entry in self._queue:
            if str(entry.event.event_id) == str(event_id):
                return entry
        return None
