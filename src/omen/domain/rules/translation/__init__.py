"""Impact translation rules."""

from omen.domain.rules.translation.base import ImpactTranslationRule
from omen.domain.rules.translation.logistics.red_sea_disruption import (
    RedSeaDisruptionRule,
)

try:
    from omen.domain.rules.translation.logistics.port_closure import PortClosureRule
    from omen.domain.rules.translation.logistics.strike_impact import StrikeImpactRule
except ImportError:
    PortClosureRule = None  # type: ignore[misc, assignment]
    StrikeImpactRule = None  # type: ignore[misc, assignment]

__all__ = [
    "ImpactTranslationRule",
    "RedSeaDisruptionRule",
    "PortClosureRule",
    "StrikeImpactRule",
]
