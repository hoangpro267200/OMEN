"""Performance metrics collection for OMEN."""

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import Lock


@dataclass
class LatencyStats:
    """Latency statistics over a time window."""

    count: int = 0
    total_ms: float = 0.0
    min_ms: float = float("inf")
    max_ms: float = 0.0
    samples: deque = field(default_factory=lambda: deque(maxlen=1000))

    def record(self, latency_ms: float) -> None:
        self.count += 1
        self.total_ms += latency_ms
        self.min_ms = min(self.min_ms, latency_ms)
        self.max_ms = max(self.max_ms, latency_ms)
        self.samples.append(latency_ms)

    @property
    def avg_ms(self) -> float:
        return self.total_ms / self.count if self.count > 0 else 0.0

    @property
    def p50_ms(self) -> float:
        if not self.samples:
            return 0.0
        sorted_samples = sorted(self.samples)
        return sorted_samples[len(sorted_samples) // 2]

    @property
    def p99_ms(self) -> float:
        if not self.samples:
            return 0.0
        sorted_samples = sorted(self.samples)
        idx = int(len(sorted_samples) * 0.99)
        return sorted_samples[min(idx, len(sorted_samples) - 1)]


@dataclass
class ThroughputStats:
    """Throughput statistics."""

    events_processed: int = 0
    events_succeeded: int = 0
    events_failed: int = 0
    window_start: datetime = field(default_factory=datetime.utcnow)

    @property
    def success_rate(self) -> float:
        if self.events_processed == 0:
            return 0.0
        return self.events_succeeded / self.events_processed

    @property
    def events_per_second(self) -> float:
        elapsed = (datetime.now(timezone.utc) - self.window_start).total_seconds()
        if elapsed == 0:
            return 0.0
        return self.events_processed / elapsed


class PipelineMetrics:
    """
    Metrics collector for OMEN pipeline.

    Thread-safe metrics collection for monitoring and alerting.
    """

    def __init__(self) -> None:
        self._lock = Lock()
        self._latency = LatencyStats()
        self._throughput = ThroughputStats()
        self._validation_latency = LatencyStats()
        self._translation_latency = LatencyStats()

    def record_processing(
        self,
        total_ms: float,
        validation_ms: float,
        translation_ms: float,
        success: bool,
    ) -> None:
        """Record metrics for a processed event."""
        with self._lock:
            self._latency.record(total_ms)
            self._validation_latency.record(validation_ms)
            self._translation_latency.record(translation_ms)
            self._throughput.events_processed += 1
            if success:
                self._throughput.events_succeeded += 1
            else:
                self._throughput.events_failed += 1

    def get_stats(self) -> dict:
        """Get current metrics snapshot."""
        with self._lock:
            return {
                "latency": {
                    "total": {
                        "avg_ms": self._latency.avg_ms,
                        "p50_ms": self._latency.p50_ms,
                        "p99_ms": self._latency.p99_ms,
                        "min_ms": self._latency.min_ms if self._latency.count > 0 else 0.0,
                        "max_ms": self._latency.max_ms,
                    },
                    "validation_avg_ms": self._validation_latency.avg_ms,
                    "translation_avg_ms": self._translation_latency.avg_ms,
                },
                "throughput": {
                    "events_processed": self._throughput.events_processed,
                    "events_succeeded": self._throughput.events_succeeded,
                    "events_failed": self._throughput.events_failed,
                    "success_rate": self._throughput.success_rate,
                    "events_per_second": self._throughput.events_per_second,
                },
            }

    def reset(self) -> None:
        """Reset all metrics."""
        with self._lock:
            self._latency = LatencyStats()
            self._throughput = ThroughputStats()
            self._validation_latency = LatencyStats()
            self._translation_latency = LatencyStats()
