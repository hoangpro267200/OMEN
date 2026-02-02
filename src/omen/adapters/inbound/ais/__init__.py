"""
AIS (Automatic Identification System) adapter for OMEN.

Provides real-time vessel tracking, port congestion detection,
and chokepoint monitoring for logistics intelligence.
"""

from .config import AISConfig
from .schemas import Vessel, PortStatus, ChokePointStatus
from .mapper import AISMapper
from .source import AISSignalSource

__all__ = [
    "AISConfig",
    "Vessel",
    "PortStatus",
    "ChokePointStatus",
    "AISMapper",
    "AISSignalSource",
]
