"""
Signal quality metrics tracking.

Tracks validation outcomes for confidence calibration and quality monitoring.
"""

from collections import defaultdict
from dataclasses import dataclass, field

from omen.domain.models.common import ConfidenceLevel, ValidationStatus
from omen.domain.models.validated_signal import ValidationResult


@dataclass
class QualityMetrics:
    """Aggregated quality metrics."""

    total_received: int = 0
    total_validated: int = 0
    total_rejected: int = 0

    rejections_by_rule: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    rejections_by_status: dict[str, int] = field(default_factory=lambda: defaultdict(int))

    confidence_distribution: dict[str, int] = field(default_factory=lambda: defaultdict(int))

    avg_validation_score: float = 0.0
    _score_sum: float = field(default=0.0, repr=False)

    def record_validation(self, passed: bool, results: list[ValidationResult]) -> None:
        """Record one validation outcome."""
        self.total_received += 1

        if passed:
            self.total_validated += 1
        else:
            self.total_rejected += 1
            for result in results:
                if result.status != ValidationStatus.PASSED:
                    self.rejections_by_rule[result.rule_name] += 1
                    self.rejections_by_status[result.status.value] += 1

        # Update average score
        total_score = sum(r.score for r in results) / len(results) if results else 0.0
        self._score_sum += total_score
        self.avg_validation_score = self._score_sum / self.total_received

    def record_confidence(self, level: ConfidenceLevel) -> None:
        """Record a confidence level for distribution tracking."""
        self.confidence_distribution[level.value] += 1

    @property
    def rejection_rate(self) -> float:
        if self.total_received == 0:
            return 0.0
        return self.total_rejected / self.total_received

    @property
    def validation_rate(self) -> float:
        if self.total_received == 0:
            return 0.0
        return self.total_validated / self.total_received

    def to_dict(self) -> dict:
        return {
            "total_received": self.total_received,
            "total_validated": self.total_validated,
            "total_rejected": self.total_rejected,
            "rejection_rate": f"{self.rejection_rate:.1%}",
            "validation_rate": f"{self.validation_rate:.1%}",
            "avg_validation_score": f"{self.avg_validation_score:.2f}",
            "rejections_by_rule": dict(self.rejections_by_rule),
            "rejections_by_status": dict(self.rejections_by_status),
            "confidence_distribution": dict(self.confidence_distribution),
        }
