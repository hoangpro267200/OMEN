"""Background services for OMEN."""

from .signal_generator import (
    BackgroundSignalGenerator,
    get_background_generator,
    start_background_generator,
    stop_background_generator,
)

__all__ = [
    "BackgroundSignalGenerator",
    "get_background_generator",
    "start_background_generator",
    "stop_background_generator",
]
