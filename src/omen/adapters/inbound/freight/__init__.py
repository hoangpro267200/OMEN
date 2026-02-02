"""
Freight rates adapter for OMEN.

Provides container freight indices, rate spikes, and capacity indicators
for logistics intelligence.
"""

from .config import FreightConfig
from .schemas import FreightRate, FreightIndex, RouteCapacity
from .mapper import FreightMapper
from .source import FreightSignalSource

__all__ = [
    "FreightConfig",
    "FreightRate",
    "FreightIndex",
    "RouteCapacity",
    "FreightMapper",
    "FreightSignalSource",
]
