"""
Time provider port for deterministic time handling.

This interface allows injecting time dependencies for:
- Deterministic testing
- Replay scenarios
- Audit trail consistency
"""

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Protocol


class TimeProvider(Protocol):
    """
    Protocol for time provision.

    Implementations:
    - SystemTimeProvider: Uses real system time
    - FixedTimeProvider: Returns a fixed time (for testing)
    - ProcessingContextTimeProvider: Uses ProcessingContext time
    """

    def now(self) -> datetime:
        """Get current time as timezone-aware UTC datetime."""
        ...


class SystemTimeProvider:
    """
    Production time provider using system clock.

    Always returns timezone-aware UTC datetime.
    """

    def now(self) -> datetime:
        """Get current system time as timezone-aware UTC."""
        return datetime.now(timezone.utc)


class FixedTimeProvider:
    """
    Fixed time provider for testing and replay.

    Always returns the same configured time.
    """

    def __init__(self, fixed_time: datetime):
        """
        Initialize with a fixed time.

        Args:
            fixed_time: The time to always return (should be timezone-aware)
        """
        if fixed_time.tzinfo is None:
            fixed_time = fixed_time.replace(tzinfo=timezone.utc)
        self._time = fixed_time

    def now(self) -> datetime:
        """Return the fixed time."""
        return self._time

    def advance(self, seconds: float) -> None:
        """Advance the fixed time by given seconds (for testing)."""
        from datetime import timedelta

        self._time = self._time + timedelta(seconds=seconds)


# Default global provider (can be overridden for testing)
_default_provider: TimeProvider = SystemTimeProvider()


def get_time_provider() -> TimeProvider:
    """Get the current time provider."""
    return _default_provider


def set_time_provider(provider: TimeProvider) -> None:
    """Set the time provider (for testing)."""
    global _default_provider
    _default_provider = provider


def reset_time_provider() -> None:
    """Reset to default system time provider."""
    global _default_provider
    _default_provider = SystemTimeProvider()


def utc_now() -> datetime:
    """
    Get current UTC time from the configured provider.

    This is the preferred way to get current time in the application.
    DO NOT use datetime.now() or datetime.utcnow() directly.
    """
    return _default_provider.now()
