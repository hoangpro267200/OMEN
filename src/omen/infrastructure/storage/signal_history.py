"""
Signal history storage for tracking probability changes over time.

This provides REAL historical data, not fabricated curves.
In production, this would be backed by Redis, TimescaleDB, or similar.
"""

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional
import threading


@dataclass
class ProbabilityPoint:
    """Single probability measurement."""

    timestamp: datetime
    probability: float
    source: str  # "polymarket_gamma", "polymarket_clob", etc.
    market_id: str


class SignalHistoryStore:
    """
    Thread-safe storage for signal probability history.

    In production, this would be backed by:
    - Redis for real-time access
    - TimescaleDB/InfluxDB for time-series queries
    - S3 for archival

    For now, in-memory with TTL.
    """

    def __init__(
        self,
        max_points_per_signal: int = 1000,
        ttl_hours: int = 168,
    ):
        self._history: dict[str, list[ProbabilityPoint]] = defaultdict(list)
        self._lock = threading.RLock()
        self._max_points = max_points_per_signal
        self._ttl = timedelta(hours=ttl_hours)

    def record(
        self,
        signal_id: str,
        probability: float,
        source: str,
        market_id: str,
        timestamp: Optional[datetime] = None,
    ) -> None:
        """
        Record a probability observation.

        Call this:
        - When processing a signal from Polymarket
        - When receiving real-time price update
        - When CLOB API returns new price
        """
        point = ProbabilityPoint(
            timestamp=timestamp or datetime.now(timezone.utc),
            probability=probability,
            source=source,
            market_id=market_id,
        )

        with self._lock:
            history = self._history[signal_id]
            history.append(point)

            if len(history) > self._max_points:
                history[:] = history[-self._max_points :]

            cutoff = datetime.now(timezone.utc) - self._ttl
            history[:] = [p for p in history if p.timestamp > cutoff]

    def get_history(
        self,
        signal_id: str,
        hours: int = 24,
        max_points: int = 24,
    ) -> list[dict]:
        """
        Get probability history for a signal.

        Returns list of {"timestamp", "probability", "source"} dicts.
        Returns EMPTY LIST if no history — never fabricates.
        """
        with self._lock:
            history = self._history.get(signal_id, [])

            if not history:
                return []

            cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
            recent = [p for p in history if p.timestamp > cutoff]

            if not recent:
                return []

            if len(recent) > max_points:
                step = len(recent) / max_points
                recent = [recent[int(i * step)] for i in range(max_points)]

            return [
                {
                    "timestamp": p.timestamp.isoformat(),
                    "probability": p.probability,
                    "source": p.source,
                }
                for p in recent
            ]

    def get_probability_series(
        self,
        signal_id: str,
        hours: int = 24,
        max_points: int = 24,
    ) -> list[float]:
        """
        Get probability values only (for API response).

        Returns empty list if no history — never fabricates.
        """
        raw = self.get_history(signal_id, hours=hours, max_points=max_points)
        return [p["probability"] for p in raw]

    def get_momentum(
        self,
        signal_id: str,
        window_hours: int = 6,
    ) -> str:
        """
        Calculate momentum from REAL history.

        Returns:
        - "INCREASING" if recent trend is up
        - "DECREASING" if recent trend is down
        - "STABLE" if no significant change
        - "UNKNOWN" if insufficient data
        """
        with self._lock:
            history = self._history.get(signal_id, [])

            if len(history) < 2:
                return "UNKNOWN"

            cutoff = datetime.now(timezone.utc) - timedelta(hours=window_hours)
            recent = [p for p in history if p.timestamp > cutoff]

            if len(recent) < 2:
                return "UNKNOWN"

            first_prob = recent[0].probability
            last_prob = recent[-1].probability
            change = last_prob - first_prob

            if change > 0.05:
                return "INCREASING"
            elif change < -0.05:
                return "DECREASING"
            else:
                return "STABLE"


_signal_history: SignalHistoryStore | None = None
_history_lock = threading.Lock()


def get_signal_history_store() -> SignalHistoryStore:
    """Return the global signal history store instance (lazy init)."""
    global _signal_history
    with _history_lock:
        if _signal_history is None:
            _signal_history = SignalHistoryStore()
        return _signal_history
