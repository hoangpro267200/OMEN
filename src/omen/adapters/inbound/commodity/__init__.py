"""
Commodity Prices Signal Source for OMEN.

Provides macro/leading indicators through commodity price monitoring
and spike detection.
"""

from .config import CommodityConfig
from .schemas import CommodityPrice, CommoditySpike
from .source import CommoditySignalSource, create_commodity_source
from .mapper import CommodityMapper
from .spike_detector import SpikeDetector

__all__ = [
    "CommodityConfig",
    "CommodityPrice",
    "CommoditySpike",
    "CommoditySignalSource",
    "create_commodity_source",
    "CommodityMapper",
    "SpikeDetector",
]
