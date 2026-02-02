"""
Security audit logging for OMEN.
"""

import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum
from functools import wraps
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
                timestamp=datetime.now(timezone.utc),
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
                timestamp=datetime.now(timezone.utc),
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
                timestamp=datetime.now(timezone.utc),
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
                timestamp=datetime.now(timezone.utc),
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

# Structured audit log for sensitive operations (actor, resource, action)
audit_logger = logging.getLogger("omen.audit")


@dataclass
class AuditEventStructured:
    """Structured audit event for sensitive operations."""

    timestamp: str
    event_type: str
    actor: str  # API key ID or "system"
    resource: str
    action: str
    status: str  # "success" or "failure"
    details: dict[str, Any] | None = None
    ip_address: str | None = None


def log_audit_event(event: AuditEventStructured) -> None:
    """Log audit event in structured JSON format."""
    audit_logger.info(json.dumps(asdict(event), default=str))


def audit_action(event_type: str, resource: str, action: str):
    """Decorator to log audit event on success/failure."""

    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            request = kwargs.get("request") or (args[0] if args else None)
            actor = (
                getattr(request.state, "api_key_id", "unknown")
                if request and hasattr(request, "state")
                else "system"
            )
            ip = (
                request.client.host
                if request and getattr(request, "client", None)
                else None
            )
            try:
                result = await func(*args, **kwargs)
                log_audit_event(
                    AuditEventStructured(
                        timestamp=datetime.now(timezone.utc).isoformat() + "Z",
                        event_type=event_type,
                        actor=actor,
                        resource=resource,
                        action=action,
                        status="success",
                        ip_address=ip,
                    )
                )
                return result
            except Exception as e:
                log_audit_event(
                    AuditEventStructured(
                        timestamp=datetime.now(timezone.utc).isoformat() + "Z",
                        event_type=event_type,
                        actor=actor,
                        resource=resource,
                        action=action,
                        status="failure",
                        details={"error": str(e)},
                        ip_address=ip,
                    )
                )
                raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            request = kwargs.get("request") or (args[0] if args else None)
            actor = (
                getattr(request.state, "api_key_id", "unknown")
                if request and hasattr(request, "state")
                else "system"
            )
            ip = (
                request.client.host
                if request and getattr(request, "client", None)
                else None
            )
            try:
                result = func(*args, **kwargs)
                log_audit_event(
                    AuditEventStructured(
                        timestamp=datetime.now(timezone.utc).isoformat() + "Z",
                        event_type=event_type,
                        actor=actor,
                        resource=resource,
                        action=action,
                        status="success",
                        ip_address=ip,
                    )
                )
                return result
            except Exception as e:
                log_audit_event(
                    AuditEventStructured(
                        timestamp=datetime.now(timezone.utc).isoformat() + "Z",
                        event_type=event_type,
                        actor=actor,
                        resource=resource,
                        action=action,
                        status="failure",
                        details={"error": str(e)},
                        ip_address=ip,
                    )
                )
                raise

        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


def get_audit_logger() -> AuditLogger:
    """Return the global audit logger instance."""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger
