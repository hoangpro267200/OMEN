"""
Activity logging — REAL events from pipeline execution.

NOT pre-populated demo data.
"""

from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal, Optional
import threading
import uuid

ActivityType = Literal["signal", "validation", "rule", "alert", "source", "error", "system"]


@dataclass
class ActivityEvent:
    """A real activity event from the system."""

    id: str
    type: ActivityType
    message: str
    timestamp: datetime

    signal_id: Optional[str] = None
    event_id: Optional[str] = None
    rule_name: Optional[str] = None
    confidence_label: Optional[str] = None
    source_name: Optional[str] = None
    error_code: Optional[str] = None

    def to_dict(self) -> dict:
        details: dict = {}
        if self.signal_id is not None:
            details["signal_id"] = self.signal_id
        if self.event_id is not None:
            details["event_id"] = self.event_id
        if self.rule_name is not None:
            details["rule_name"] = self.rule_name
        if self.confidence_label is not None:
            details["confidence_level"] = self.confidence_label
        if self.source_name is not None:
            details["source_name"] = self.source_name
        if self.error_code is not None:
            details["error_code"] = self.error_code
        return {
            "id": self.id,
            "type": self.type,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
            "details": details,
        }


class ActivityLogger:
    """
    Logs real activity events from the OMEN system.

    Call log_* from pipeline, data sources, and API.
    """

    def __init__(self, max_events: int = 1000):
        self._events: deque[ActivityEvent] = deque(maxlen=max_events)
        self._lock = threading.RLock()

    def _log(self, event: ActivityEvent) -> None:
        with self._lock:
            self._events.append(event)

    def log_signal_generated(
        self,
        signal_id: str,
        title: str,
        confidence_label: str,
        confidence_level: str,
    ) -> None:
        """Log when a signal is generated."""
        self._log(
            ActivityEvent(
                id=str(uuid.uuid4())[:8],
                type="signal",
                message=f"Tín hiệu được tạo: {signal_id} — {(title or '')[:50]}",
                timestamp=datetime.now(timezone.utc),
                signal_id=signal_id,
                confidence_label=confidence_label,
            )
        )
        if confidence_label in ("HIGH", "VERY_HIGH", "CRITICAL"):
            self._log(
                ActivityEvent(
                    id=str(uuid.uuid4())[:8],
                    type="alert",
                    message=f"High-confidence signal ({confidence_label}): {signal_id}",
                    timestamp=datetime.now(timezone.utc),
                    signal_id=signal_id,
                    confidence_label=confidence_label,
                )
            )

    def log_event_validated(
        self,
        event_id: str,
        market_id: str,
        rule_name: str,
        passed: bool,
        reason: Optional[str] = None,
    ) -> None:
        """Log when an event passes or fails validation."""
        short_id = (market_id or event_id or "")[:20]
        if passed:
            self._log(
                ActivityEvent(
                    id=str(uuid.uuid4())[:8],
                    type="validation",
                    message=f"Sự kiện đã được xác thực: {short_id}...",
                    timestamp=datetime.now(timezone.utc),
                    event_id=event_id,
                    rule_name=rule_name,
                )
            )
        else:
            self._log(
                ActivityEvent(
                    id=str(uuid.uuid4())[:8],
                    type="validation",
                    message=f"Sự kiện bị từ chối: {short_id}... — {reason or 'Unknown'}",
                    timestamp=datetime.now(timezone.utc),
                    event_id=event_id,
                    rule_name=rule_name,
                )
            )

    def log_rule_applied(
        self,
        rule_name: str,
        rule_version: str,
        signal_id: Optional[str] = None,
        contribution: Optional[float] = None,
    ) -> None:
        """Log when a translation rule is applied."""
        contrib = f" ({contribution:.0%})" if contribution is not None else ""
        self._log(
            ActivityEvent(
                id=str(uuid.uuid4())[:8],
                type="rule",
                message=f"Quy tắc được áp dụng: {rule_name} v{rule_version}{contrib}",
                timestamp=datetime.now(timezone.utc),
                signal_id=signal_id or None,
                rule_name=rule_name,
            )
        )

    def log_source_fetch(
        self,
        source_name: str,
        events_count: int,
        latency_ms: float,
        success: bool,
        error_message: Optional[str] = None,
    ) -> None:
        """Log data source fetch results."""
        if success:
            self._log(
                ActivityEvent(
                    id=str(uuid.uuid4())[:8],
                    type="source",
                    message=f"{source_name}: Đã nhận {events_count} sự kiện ({latency_ms:.0f}ms)",
                    timestamp=datetime.now(timezone.utc),
                    source_name=source_name,
                )
            )
        else:
            self._log(
                ActivityEvent(
                    id=str(uuid.uuid4())[:8],
                    type="error",
                    message=f"{source_name}: Lỗi kết nối — {error_message or 'Unknown'}",
                    timestamp=datetime.now(timezone.utc),
                    source_name=source_name,
                    error_code=error_message,
                )
            )

    def log_system_event(self, message: str) -> None:
        """Log a general system event."""
        self._log(
            ActivityEvent(
                id=str(uuid.uuid4())[:8],
                type="system",
                message=message,
                timestamp=datetime.now(timezone.utc),
            )
        )

    def get_recent(self, limit: int = 50) -> list[dict]:
        """Get recent activity events (newest first)."""
        with self._lock:
            events = list(self._events)[-limit:]
            return [e.to_dict() for e in reversed(events)]


_activity_logger: Optional[ActivityLogger] = None
_activity_lock = threading.Lock()


def get_activity_logger() -> ActivityLogger:
    """Get or create the global activity logger."""
    global _activity_logger
    with _activity_lock:
        if _activity_logger is None:
            _activity_logger = ActivityLogger()
        return _activity_logger
