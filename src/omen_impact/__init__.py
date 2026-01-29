"""
OMEN Impact Assessment Module

ARCHITECTURAL NOTE:
This module is ISOLATED from OMEN core.
Impact assessment is a CONSUMER responsibility, not a signal engine function.
This code will be migrated to RiskCast.
"""

from omen_impact.assessment import (
    ImpactAssessment,
    ImpactMetric,
    AffectedRoute,
    AffectedSystem,
    UncertaintyBounds,
)
from omen_impact.translator import ImpactTranslator
from omen_impact.legacy_signal import LegacyOmenSignal
from omen_impact.legacy_pipeline import LegacyPipeline

__all__ = [
    "ImpactTranslator",
    "ImpactAssessment",
    "AffectedRoute",
    "AffectedSystem",
    "ImpactMetric",
    "UncertaintyBounds",
    "LegacyOmenSignal",
    "LegacyPipeline",
]
