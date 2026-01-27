"""FastAPI dependencies."""

from omen.application.container import get_container
from omen.application.ports.signal_repository import SignalRepository


def get_repository() -> SignalRepository:
    """Return the signal repository from the application container."""
    return get_container().repository
