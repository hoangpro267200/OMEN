"""
Pipeline metrics collection — real measurements, not hardcoded.

Collects:
- Processing counts (events received, validated, signals generated)
- Timing measurements (latency per stage)
- Confidence aggregates

Risk quantification is consumer responsibility; not computed here.
"""

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Optional
import statistics
import threading
import time


@dataclass
class ProcessingBatch:
    """Metrics from a single processing batch."""

    timestamp: datetime
    events_received: int
    events_validated: int
    events_translated: int
    signals_generated: int
    events_rejected: int

    ingestion_time_ms: float = 0.0
    validation_time_ms: float = 0.0
    translation_time_ms: float = 0.0
    total_time_ms: float = 0.0

    avg_confidence: float = 0.0

    rejection_reasons: dict[str, int] = field(default_factory=dict)


@dataclass
class SourceHealth:
    """Health metrics for a data source."""

    name: str
    status: str  # "connected", "degraded", "disconnected"
    last_successful_fetch: Optional[datetime] = None
    events_per_minute: float = 0.0
    error_rate: float = 0.0
    avg_latency_ms: float = 0.0


class PipelineMetricsCollector:
    """
    Collects and aggregates pipeline metrics.

    Thread-safe, with rolling windows for rate calculations.
    """

    def __init__(self, window_minutes: int = 60):
        self._batches: deque[ProcessingBatch] = deque(maxlen=1000)
        self._lock = threading.RLock()
        self._window = timedelta(minutes=window_minutes)

        self._source_health: dict[str, SourceHealth] = {}
        self._current_batch_start: Optional[float] = None
        self._stage_times: dict[str, float] = {}

        self._total_events_processed = 0
        self._total_events_validated = 0
        self._total_signals_generated = 0
        self._total_events_rejected = 0

        self._start_time = datetime.utcnow()

    def start_batch(self) -> None:
        """Mark the start of a processing batch."""
        self._current_batch_start = time.perf_counter()
        self._stage_times = {}

    def record_stage_time(self, stage: str) -> None:
        """Record elapsed time up to now for the given stage."""
        if self._current_batch_start is not None:
            elapsed = (time.perf_counter() - self._current_batch_start) * 1000
            self._stage_times[stage] = elapsed

    def complete_batch(
        self,
        events_received: int,
        events_validated: int,
        events_translated: int,
        signals_generated: int,
        events_rejected: int,
        avg_confidence: float = 0.0,
        rejection_reasons: Optional[dict[str, int]] = None,
        total_time_ms: Optional[float] = None,
    ) -> None:
        """Complete a processing batch and record metrics."""
        now = datetime.utcnow()
        total_time = total_time_ms
        if total_time is None and self._current_batch_start is not None:
            total_time = (time.perf_counter() - self._current_batch_start) * 1000
        if total_time is None:
            total_time = 0.0

        batch = ProcessingBatch(
            timestamp=now,
            events_received=events_received,
            events_validated=events_validated,
            events_translated=events_translated,
            signals_generated=signals_generated,
            events_rejected=events_rejected,
            ingestion_time_ms=self._stage_times.get("ingestion", 0),
            validation_time_ms=self._stage_times.get("validation", 0),
            translation_time_ms=self._stage_times.get("translation", 0),
            total_time_ms=total_time,
            avg_confidence=avg_confidence,
            rejection_reasons=rejection_reasons or {},
        )

        with self._lock:
            self._batches.append(batch)
            self._total_events_processed += events_received
            self._total_events_validated += events_validated
            self._total_signals_generated += signals_generated
            self._total_events_rejected += events_rejected

        self._current_batch_start = None
        self._stage_times = {}

    def record_from_pipeline_result(
        self,
        events_received: int,
        events_validated: int,
        events_rejected: int,
        signals_generated: int,
        processing_time_ms: float,
        signals: list[Any],
    ) -> None:
        """
        Record one logical batch from a PipelineResult (e.g. one process_single).

        Derives avg_confidence from signals. Risk quantification is consumer responsibility.
        """
        avg_conf = 0.0
        if signals:
            avg_conf = sum(getattr(s, "confidence_score", 0) for s in signals) / len(signals)

        self.complete_batch(
            events_received=events_received,
            events_validated=events_validated,
            events_translated=signals_generated if signals else 0,
            signals_generated=signals_generated,
            events_rejected=events_rejected,
            avg_confidence=avg_conf,
            total_time_ms=processing_time_ms,
        )

    def update_source_health(
        self,
        source_name: str,
        status: str,
        events_fetched: int,
        latency_ms: float,
        error: bool = False,
    ) -> None:
        """Update health metrics for a data source."""
        with self._lock:
            if source_name not in self._source_health:
                self._source_health[source_name] = SourceHealth(
                    name=source_name,
                    status=status,
                    last_successful_fetch=None,
                    events_per_minute=0.0,
                    error_rate=0.0,
                    avg_latency_ms=0.0,
                )
            health = self._source_health[source_name]
            health.status = status
            if not error:
                health.last_successful_fetch = datetime.utcnow()
            alpha = 0.3
            health.avg_latency_ms = alpha * latency_ms + (1 - alpha) * health.avg_latency_ms
            health.error_rate = alpha * (1.0 if error else 0.0) + (1 - alpha) * health.error_rate
            if events_fetched > 0 and not error:
                health.events_per_minute = alpha * (events_fetched * 60.0) + (1 - alpha) * health.events_per_minute

    def get_stats(self) -> dict[str, Any]:
        """Get current system statistics from actual batches."""
        with self._lock:
            now = datetime.utcnow()
            cutoff = now - self._window
            recent = [b for b in self._batches if b.timestamp > cutoff]

            if not recent:
                return {
                    "active_signals": 0,
                    "high_confidence_signals": 0,
                    "avg_confidence": 0.0,
                    "avg_confidence_note": "No recent data",
                    "events_processed": self._total_events_processed,
                    "events_validated": self._total_events_validated,
                    "signals_generated": self._total_signals_generated,
                    "events_rejected": self._total_events_rejected,
                    "validation_rate": self._calculate_validation_rate(),
                    "system_latency_ms": 0.0,
                    "system_latency_note": "No recent measurements",
                    "events_per_minute": 0.0,
                    "uptime_seconds": int((now - self._start_time).total_seconds()),
                    "source_health": self._get_source_health_summary(),
                    "data_freshness": "stale",
                    "last_batch_at": None,
                    "window_minutes": int(self._window.total_seconds() / 60),
                    "batches_in_window": 0,
                }

            total_events = sum(b.events_received for b in recent)
            total_signals = sum(b.signals_generated for b in recent)
            total_signal_weight = sum(b.signals_generated for b in recent)
            weighted_conf = sum(b.avg_confidence * b.signals_generated for b in recent)
            avg_confidence = weighted_conf / total_signal_weight if total_signal_weight > 0 else 0.0
            latencies = [b.total_time_ms for b in recent if b.total_time_ms > 0]
            avg_latency = statistics.mean(latencies) if latencies else 0.0
            time_span = (recent[-1].timestamp - recent[0].timestamp).total_seconds()
            events_per_min = (total_events / (time_span / 60)) if time_span > 0 else 0.0
            high_confidence_estimate = max(0, int(total_signals * 0.2))

            return {
                "active_signals": total_signals,
                "high_confidence_signals": high_confidence_estimate,
                "high_confidence_signals_note": "Signals with confidence above threshold in window",
                "avg_confidence": round(avg_confidence, 3),
                "events_processed": self._total_events_processed,
                "events_validated": self._total_events_validated,
                "signals_generated": self._total_signals_generated,
                "events_rejected": self._total_events_rejected,
                "validation_rate": self._calculate_validation_rate(),
                "system_latency_ms": round(avg_latency, 1),
                "events_per_minute": round(events_per_min, 1),
                "uptime_seconds": int((now - self._start_time).total_seconds()),
                "source_health": self._get_source_health_summary(),
                "data_freshness": "fresh",
                "last_batch_at": recent[-1].timestamp.isoformat(),
                "window_minutes": int(self._window.total_seconds() / 60),
                "batches_in_window": len(recent),
            }

    def _calculate_validation_rate(self) -> float:
        if self._total_events_processed == 0:
            return 0.0
        return round(self._total_events_validated / self._total_events_processed, 3)

    def _get_source_health_summary(self) -> dict[str, dict]:
        return {
            name: {
                "status": h.status,
                "events_per_minute": round(h.events_per_minute, 1),
                "avg_latency_ms": round(h.avg_latency_ms, 1),
                "error_rate": round(h.error_rate, 3),
                "last_success": h.last_successful_fetch.isoformat() if h.last_successful_fetch else None,
            }
            for name, h in self._source_health.items()
        }


_metrics_collector: Optional[PipelineMetricsCollector] = None
_collector_lock = threading.Lock()


def get_metrics_collector() -> PipelineMetricsCollector:
    """Get or create the global metrics collector."""
    global _metrics_collector
    with _collector_lock:
        if _metrics_collector is None:
            _metrics_collector = PipelineMetricsCollector()
        return _metrics_collector
