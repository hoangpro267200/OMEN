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
    "VALIDATION_METHODOLOGIES",
    "CONFIDENCE_METHODOLOGY",
    "LIQUIDITY_VALIDATION_METHODOLOGY",
    "GEOGRAPHIC_RELEVANCE_METHODOLOGY",
]
