"""
OMEN Error Hierarchy.

All errors are explicit, typed, and carry context for debugging.
Timestamps are injected via TimeProvider for determinism.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional


class OmenError(Exception):
    """Base error for all OMEN exceptions."""

    def __init__(
        self,
        message: str,
        context: dict[str, Any] | None = None,
        timestamp: Optional[datetime] = None,
    ):
        super().__init__(message)
        self.message = message
        self.context = context or {}
        # Use injected timestamp or get from TimeProvider
        if timestamp is not None:
            self.timestamp = timestamp
        else:
            from omen.application.ports.time_provider import utc_now

            self.timestamp = utc_now()

    def to_dict(self) -> dict[str, Any]:
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "context": self.context,
            "timestamp": self.timestamp.isoformat(),
        }


# === Source Errors ===
class SourceError(OmenError):
    """Base error for signal source failures."""

    pass


class SourceUnavailableError(SourceError):
    """Signal source is temporarily unavailable."""

    pass


class SourceRateLimitedError(SourceError):
    """Signal source rate limit exceeded."""

    def __init__(
        self,
        message: str,
        retry_after_seconds: int | None = None,
        context: dict[str, Any] | None = None,
    ):
        super().__init__(message, context=context)
        self.retry_after_seconds = retry_after_seconds


class SourceAuthenticationError(SourceError):
    """Authentication with signal source failed."""

    pass


# === Validation Errors ===
class ValidationError(OmenError):
    """Base error for validation failures."""

    pass


class ValidationRuleError(ValidationError):
    """A validation rule raised an unexpected exception."""

    def __init__(
        self,
        message: str,
        rule_name: str,
        context: dict[str, Any] | None = None,
    ):
        super().__init__(message, context=context)
        self.rule_name = rule_name


# === Translation Errors ===
class TranslationError(OmenError):
    """Base error for translation failures."""

    pass


class TranslationRuleError(TranslationError):
    """A translation rule raised an unexpected exception."""

    def __init__(
        self,
        message: str,
        rule_name: str,
        domain: str,
        context: dict[str, Any] | None = None,
    ):
        super().__init__(message, context=context)
        self.rule_name = rule_name
        self.domain = domain


class NoApplicableRulesError(TranslationError):
    """No translation rules were applicable for this signal."""

    pass


# === Persistence Errors ===
class PersistenceError(OmenError):
    """Base error for repository failures."""

    pass


class SignalNotFoundError(PersistenceError):
    """Requested signal does not exist."""

    def __init__(
        self,
        signal_id: str,
        context: dict[str, Any] | None = None,
    ):
        super().__init__(f"Signal not found: {signal_id}", context=context)
        self.signal_id = signal_id


class DuplicateSignalError(PersistenceError):
    """Signal with this ID already exists."""

    pass


# === Publishing Errors ===
class PublishError(OmenError):
    """Base error for output publishing failures."""

    pass


class PublishTimeoutError(PublishError):
    """Publishing timed out."""

    pass


class PublishRetriesExhaustedError(PublishError):
    """All publish retry attempts failed."""

    def __init__(
        self,
        message: str,
        attempts: int,
        context: dict[str, Any] | None = None,
    ):
        super().__init__(message, context=context)
        self.attempts = attempts


# === Pipeline Errors ===
class PipelineError(OmenError):
    """Base error for pipeline-level failures."""

    pass


class PipelineConfigurationError(PipelineError):
    """Pipeline is misconfigured."""

    pass
