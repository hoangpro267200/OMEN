"""
Methodology documentation system.

Every calculation in OMEN must have:
1. Documented formula
2. Cited source(s)
3. Stated assumptions
4. Known limitations
5. Validation status
6. Version history
"""

from .base import Methodology, SourceCitation, ValidationStatus
from .red_sea_impact import (
    RED_SEA_METHODOLOGIES,
    get_methodology,
    get_all_methodologies,
    TRANSIT_TIME_METHODOLOGY,
    FUEL_COST_METHODOLOGY,
    FREIGHT_RATE_METHODOLOGY,
    INSURANCE_METHODOLOGY,
    TIMING_METHODOLOGY,
)
from .validation_rules import (
    VALIDATION_METHODOLOGIES,
    LIQUIDITY_VALIDATION_METHODOLOGY,
    GEOGRAPHIC_RELEVANCE_METHODOLOGY,
    CONFIDENCE_METHODOLOGY,
)

__all__ = [
    "Methodology",
    "SourceCitation",
    "ValidationStatus",
    "RED_SEA_METHODOLOGIES",
    "VALIDATION_METHODOLOGIES",
    "CONFIDENCE_METHODOLOGY",
    "get_methodology",
    "get_all_methodologies",
    "TRANSIT_TIME_METHODOLOGY",
    "FUEL_COST_METHODOLOGY",
    "FREIGHT_RATE_METHODOLOGY",
    "INSURANCE_METHODOLOGY",
    "TIMING_METHODOLOGY",
    "LIQUIDITY_VALIDATION_METHODOLOGY",
    "GEOGRAPHIC_RELEVANCE_METHODOLOGY",
]
