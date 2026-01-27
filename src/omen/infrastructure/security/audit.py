"""
Security audit logging for OMEN.
"""

import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Literal


class AuditEventType(str, Enum):
    """Types of security events to audit."""

    AUTH_SUCCESS = "auth.success"
    AUTH_FAILURE = "auth.failure"
    RATE_LIMIT_HIT = "rate_limit.hit"
    INPUT_VALIDATION_FAILURE = "input.validation_failure"
    SIGNAL_CREATED = "signal.created"
    SIGNAL_ACCESSED = "signal.accessed"
    WEBHOOK_SENT = "webhook.sent"
    WEBHOOK_FAILED = "webhook.failed"
    CONFIG_CHANGED = "config.changed"


@dataclass
class AuditEvent:
    """A security audit event."""

    timestamp: datetime
    event_type: AuditEventType
    client_id: str | None
    ip_address: str | None
    resource: str | None
    action: str
    outcome: Literal["success", "failure"]
    details: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize for JSON logging."""
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        data["event_type"] = self.event_type.value
        return data


class AuditLogger:
    """
    Security audit logger.

    Logs security-relevant events for compliance and forensics.
    """

    def __init__(self, logger_name: str = "omen.security.audit"):
        self._logger = logging.getLogger(logger_name)
        self._logger.setLevel(logging.INFO)

        if not self._logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(
                logging.Formatter(
                    '"timestamp": "%(asctime)s", "level": "%(levelname)s", '
                    '"logger": "%(name)s", "event": %(message)s'
                )
            )
            self._logger.addHandler(handler)

    def log(self, event: AuditEvent) -> None:
        """Log an audit event."""
        self._logger.info(json.dumps(event.to_dict()))

    def auth_success(
        self,
        client_id: str,
        ip_address: str,
        auth_method: str,
    ) -> None:
        """Log successful authentication."""
        self.log(
            AuditEvent(
                timestamp=datetime.utcnow(),
                event_type=AuditEventType.AUTH_SUCCESS,
                client_id=client_id,
                ip_address=ip_address,
                resource=None,
                action="authenticate",
                outcome="success",
                details={"method": auth_method},
            )
        )

    def auth_failure(
        self,
        ip_address: str,
        reason: str,
        auth_method: str,
    ) -> None:
        """Log failed authentication."""
        self.log(
            AuditEvent(
                timestamp=datetime.utcnow(),
                event_type=AuditEventType.AUTH_FAILURE,
                client_id=None,
                ip_address=ip_address,
                resource=None,
                action="authenticate",
                outcome="failure",
                details={"method": auth_method, "reason": reason},
            )
        )

    def rate_limit_hit(
        self,
        client_id: str,
        ip_address: str,
        endpoint: str,
    ) -> None:
        """Log rate limit exceeded."""
        self.log(
            AuditEvent(
                timestamp=datetime.utcnow(),
                event_type=AuditEventType.RATE_LIMIT_HIT,
                client_id=client_id,
                ip_address=ip_address,
                resource=endpoint,
                action="request",
                outcome="failure",
                details={"reason": "rate_limit_exceeded"},
            )
        )

    def signal_accessed(
        self,
        client_id: str,
        signal_id: str,
        detail_level: str,
    ) -> None:
        """Log signal access."""
        self.log(
            AuditEvent(
                timestamp=datetime.utcnow(),
                event_type=AuditEventType.SIGNAL_ACCESSED,
                client_id=client_id,
                ip_address=None,
                resource=signal_id,
                action="read",
                outcome="success",
                details={"detail_level": detail_level},
            )
        )


_audit_logger: AuditLogger | None = None


def get_audit_logger() -> AuditLogger:
    """Return the global audit logger instance."""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger
