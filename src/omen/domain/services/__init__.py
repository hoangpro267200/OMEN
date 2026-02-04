"""Domain services.

✅ ACTIVATED: All domain services are now exported and available.
"""

from omen.domain.services.signal_validator import SignalValidator
from omen.domain.services.signal_classifier import SignalClassifier
from omen.domain.services.conflict_detector import (
    SignalConflictDetector,
    ConflictResult,
    ConflictSeverity,
)
from omen.domain.services.source_trust_manager import (
    SourceTrustManager,
    SourceTrustScore,
    TrustLevel,
    get_trust_manager,
)
from omen.domain.services.historical_validation import (
    HistoricalValidator,
    PredictionRecord,
    OutcomeRecord,
    CalibrationComparison,
    CalibrationReport,
)
from omen.domain.services.quality_metrics import QualityMetrics

# ✅ NEW: EnhancedConfidenceCalculator with confidence intervals
from omen.domain.services.confidence_calculator import (
    EnhancedConfidenceCalculator,
    ConfidenceInterval,
    get_confidence_calculator,
    calculate_confidence_interval,
)

# ✅ NEW: ExplanationBuilder for programmatic explanations
from omen.domain.services.explanation_builder import ExplanationBuilder

# Note: explanation_report is imported lazily to avoid circular imports
# Use: from omen.domain.services.explanation_report import generate_text_report
def generate_text_report(signal):
    """Generate text report for a signal (lazy import to avoid circular deps)."""
    from omen.domain.services.explanation_report import generate_text_report as _gen
    return _gen(signal)

def generate_json_audit_report(signal):
    """Generate JSON audit report for a signal (lazy import)."""
    from omen.domain.services.explanation_report import generate_json_audit_report as _gen
    return _gen(signal)

# Global instances
_historical_validator: HistoricalValidator | None = None
_quality_metrics: QualityMetrics | None = None


def get_historical_validator() -> HistoricalValidator:
    """Get or create the global historical validator."""
    global _historical_validator
    if _historical_validator is None:
        _historical_validator = HistoricalValidator()
    return _historical_validator


def get_quality_metrics() -> QualityMetrics:
    """Get or create the global quality metrics tracker."""
    global _quality_metrics
    if _quality_metrics is None:
        _quality_metrics = QualityMetrics()
    return _quality_metrics


__all__ = [
    # Core validation
    "SignalValidator",
    "SignalClassifier",
    "SignalConflictDetector",
    "ConflictResult",
    "ConflictSeverity",
    # Source trust
    "SourceTrustManager",
    "SourceTrustScore",
    "TrustLevel",
    "get_trust_manager",
    # Historical validation
    "HistoricalValidator",
    "PredictionRecord",
    "OutcomeRecord",
    "CalibrationComparison",
    "CalibrationReport",
    "get_historical_validator",
    # Quality metrics
    "QualityMetrics",
    "get_quality_metrics",
    # ✅ NEW: Enhanced confidence with intervals
    "EnhancedConfidenceCalculator",
    "ConfidenceInterval",
    "get_confidence_calculator",
    "calculate_confidence_interval",
    # ✅ NEW: Explanation building
    "ExplanationBuilder",
    "generate_text_report",
    "generate_json_audit_report",
]
