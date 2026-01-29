"""Impact methodology documentation (Red Sea, etc.). Uses omen.domain.methodology.base for types."""

from omen.domain.methodology.base import Methodology, SourceCitation, ValidationStatus
from .red_sea_impact import (
    RED_SEA_METHODOLOGIES,
    TIMING_METHODOLOGY,
    get_methodology,
    get_all_methodologies,
)

__all__ = [
    "Methodology",
    "SourceCitation",
    "ValidationStatus",
    "RED_SEA_METHODOLOGIES",
    "TIMING_METHODOLOGY",
    "get_methodology",
    "get_all_methodologies",
]
