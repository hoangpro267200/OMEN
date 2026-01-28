"""
Tracks and exposes rejection reasons for debugging and transparency.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Optional
import threading

RejectionStage = Literal[
    "ingestion",
    "mapping",
    "validation",
    "translation",
    "generation",
]


@dataclass
class RejectionRecord:
    """Record of a rejected event."""

    event_id: str
    stage: RejectionStage
    reason: str
    timestamp: datetime

    title: Optional[str] = None
    probability: Optional[float] = None
    liquidity: Optional[float] = None
    keywords_found: list[str] = None

    rule_name: Optional[str] = None
    rule_version: Optional[str] = None
    details: dict = None

    def __post_init__(self) -> None:
        if self.keywords_found is None:
            self.keywords_found = []
        if self.details is None:
            self.details = {}

    def to_dict(self) -> dict:
        return {
            "event_id": self.event_id,
            "stage": self.stage,
            "reason": self.reason,
            "timestamp": self.timestamp.isoformat(),
            "title": self.title,
            "probability": self.probability,
            "liquidity": self.liquidity,
            "keywords_found": self.keywords_found,
            "rule_name": self.rule_name,
            "rule_version": self.rule_version,
            "details": self.details,
        }


@dataclass
class PassedRecord:
    """Record of a passed/generated signal."""

    signal_id: str
    event_id: str
    stage: str
    timestamp: datetime

    title: str
    probability: float
    confidence: float
    severity: str

    metrics_count: int = 0
    routes_count: int = 0

    def to_dict(self) -> dict:
        return {
            "signal_id": self.signal_id,
            "event_id": self.event_id,
            "stage": self.stage,
            "timestamp": self.timestamp.isoformat(),
            "title": self.title,
            "probability": self.probability,
            "confidence": self.confidence,
            "severity": self.severity,
            "metrics_count": self.metrics_count,
            "routes_count": self.routes_count,
        }


class RejectionTracker:
    """
    Tracks rejected and passed events through the pipeline.

    Provides visibility into why events are rejected at each stage
    and what events passed and became signals.
    """

    def __init__(self, max_records: int = 500) -> None:
        self._rejections: deque[RejectionRecord] = deque(maxlen=max_records)
        self._passed: deque[PassedRecord] = deque(maxlen=max_records)
        self._lock = threading.RLock()

        self._rejection_counts: dict[str, int] = {
            "ingestion": 0,
            "mapping": 0,
            "validation": 0,
            "translation": 0,
            "generation": 0,
        }
        self._passed_count: int = 0

    def record_rejection(
        self,
        event_id: str,
        stage: RejectionStage,
        reason: str,
        title: Optional[str] = None,
        probability: Optional[float] = None,
        liquidity: Optional[float] = None,
        keywords_found: Optional[list[str]] = None,
        rule_name: Optional[str] = None,
        rule_version: Optional[str] = None,
        details: Optional[dict] = None,
    ) -> None:
        """Record a rejection."""
        record = RejectionRecord(
            event_id=event_id,
            stage=stage,
            reason=reason,
            timestamp=datetime.utcnow(),
            title=title,
            probability=probability,
            liquidity=liquidity,
            keywords_found=keywords_found or [],
            rule_name=rule_name,
            rule_version=rule_version,
            details=details or {},
        )

        with self._lock:
            self._rejections.append(record)
            self._rejection_counts[stage] = self._rejection_counts.get(stage, 0) + 1

    def record_passed(
        self,
        signal_id: str,
        event_id: str,
        title: str,
        probability: float,
        confidence: float,
        severity: str,
        metrics_count: int = 0,
        routes_count: int = 0,
    ) -> None:
        """Record a successfully generated signal."""
        record = PassedRecord(
            signal_id=signal_id,
            event_id=event_id,
            stage="generated",
            timestamp=datetime.utcnow(),
            title=title,
            probability=probability,
            confidence=confidence,
            severity=severity,
            metrics_count=metrics_count,
            routes_count=routes_count,
        )

        with self._lock:
            self._passed.append(record)
            self._passed_count += 1

    def get_recent_rejections(
        self,
        limit: int = 50,
        stage: Optional[RejectionStage] = None,
    ) -> list[dict]:
        """Get recent rejections, optionally filtered by stage."""
        with self._lock:
            records = list(self._rejections)

            if stage:
                records = [r for r in records if r.stage == stage]

            return [r.to_dict() for r in reversed(records[-limit:])]

    def get_recent_passed(self, limit: int = 50) -> list[dict]:
        """Get recently passed/generated signals."""
        with self._lock:
            records = list(self._passed)
            return [r.to_dict() for r in reversed(records[-limit:])]

    def get_passed_count(self) -> int:
        """Total number of signals generated (passed)."""
        with self._lock:
            return self._passed_count

    def get_statistics(self) -> dict:
        """Get rejection statistics."""
        with self._lock:
            total_rejected = sum(self._rejection_counts.values())
            total_processed = total_rejected + self._passed_count

            return {
                "total_processed": total_processed,
                "total_rejected": total_rejected,
                "total_passed": self._passed_count,
                "pass_rate": self._passed_count / total_processed if total_processed > 0 else 0,
                "rejection_rate": total_rejected / total_processed if total_processed > 0 else 0,
                "by_stage": {
                    stage: {
                        "count": count,
                        "percentage": count / total_rejected if total_rejected > 0 else 0,
                    }
                    for stage, count in self._rejection_counts.items()
                },
                "top_rejection_reasons": self._get_top_reasons(10),
            }

    def _get_top_reasons(self, limit: int) -> list[dict]:
        """Get most common rejection reasons."""
        reason_counts: dict[str, int] = {}

        for record in self._rejections:
            key = f"{record.stage}:{record.reason[:50]}"
            reason_counts[key] = reason_counts.get(key, 0) + 1

        sorted_reasons = sorted(reason_counts.items(), key=lambda x: x[1], reverse=True)

        return [{"reason": reason, "count": count} for reason, count in sorted_reasons[:limit]]

    def clear(self) -> None:
        """Clear all records."""
        with self._lock:
            self._rejections.clear()
            self._passed.clear()
            self._rejection_counts = {k: 0 for k in self._rejection_counts}
            self._passed_count = 0


_rejection_tracker: Optional[RejectionTracker] = None


def get_rejection_tracker() -> RejectionTracker:
    """Return the global RejectionTracker instance."""
    global _rejection_tracker
    if _rejection_tracker is None:
        _rejection_tracker = RejectionTracker()
    return _rejection_tracker
