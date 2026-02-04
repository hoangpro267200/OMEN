"""Ports (interfaces) for hexagonal architecture.

Note: Using lazy imports to avoid circular dependencies with domain models.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from omen.application.ports.output_publisher import OutputPublisher
    from omen.application.ports.signal_repository import AsyncSignalRepository, SignalRepository
    from omen.application.ports.signal_source import SignalSource

__all__ = [
    "AsyncSignalRepository",
    "SignalRepository",
    "SignalSource",
    "OutputPublisher",
]


def __getattr__(name: str):
    """Lazy import to avoid circular dependencies."""
    if name == "OutputPublisher":
        from omen.application.ports.output_publisher import OutputPublisher
        return OutputPublisher
    if name == "AsyncSignalRepository":
        from omen.application.ports.signal_repository import AsyncSignalRepository
        return AsyncSignalRepository
    if name == "SignalRepository":
        from omen.application.ports.signal_repository import SignalRepository
        return SignalRepository
    if name == "SignalSource":
        from omen.application.ports.signal_source import SignalSource
        return SignalSource
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
