"""
Historical Validation Framework.

Compares OMEN predictions against actual outcomes for calibration.
"""

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class PredictionRecord:
    """A historical prediction to validate. Immutable."""

    signal_id: str
    metric_name: str
    predicted_value: float
    predicted_lower: float | None
    predicted_upper: float | None
    prediction_date: datetime
    event_probability: float


@dataclass(frozen=True)
class OutcomeRecord:
    """Actual outcome for validation. Immutable."""

    signal_id: str
    metric_name: str
    actual_value: float
    outcome_date: datetime
    source: str


@dataclass(frozen=True)
class CalibrationComparison:
    """Result of validating a prediction against outcome. Immutable."""

    signal_id: str
    metric_name: str
    predicted: float
    actual: float
    error: float
    error_percent: float
    within_bounds: bool | None


@dataclass
class CalibrationReport:
    """Aggregated calibration metrics."""

    total_predictions: int = 0
    predictions_within_bounds: int = 0
    mean_absolute_error: float = 0.0
    mean_absolute_percent_error: float = 0.0

    errors_by_metric: dict[str, list[float]] = field(
        default_factory=lambda: defaultdict(list)
    )
    coverage_by_confidence: dict[str, float] = field(default_factory=dict)

    @property
    def coverage_rate(self) -> float:
        """Percentage of predictions within uncertainty bounds."""
        if self.total_predictions == 0:
            return 0.0
        return self.predictions_within_bounds / self.total_predictions

    def is_well_calibrated(self, target_coverage: float = 0.8) -> bool:
        """Check if model is well-calibrated."""
        return self.coverage_rate >= target_coverage


class HistoricalValidator:
    """
    Validates OMEN predictions against historical outcomes.

    Usage:
    1. Record predictions when signals are generated
    2. Record actual outcomes when they occur
    3. Run validate() to generate calibration report
    """

    def __init__(self) -> None:
        self._predictions: dict[str, list[PredictionRecord]] = defaultdict(list)
        self._outcomes: dict[str, OutcomeRecord] = {}

    def record_prediction(self, record: PredictionRecord) -> None:
        """Record a prediction for later validation."""
        key = f"{record.signal_id}:{record.metric_name}"
        self._predictions[key].append(record)

    def record_outcome(self, record: OutcomeRecord) -> None:
        """Record an actual outcome."""
        key = f"{record.signal_id}:{record.metric_name}"
        self._outcomes[key] = record

    def validate(
        self,
    ) -> tuple[list[CalibrationComparison], CalibrationReport]:
        """
        Validate all predictions that have outcomes.

        Returns:
            Tuple of (individual results, aggregated report)
        """
        results: list[CalibrationComparison] = []
        report = CalibrationReport()

        for key, predictions in self._predictions.items():
            outcome = self._outcomes.get(key)
            if not outcome:
                continue

            for pred in predictions:
                error = abs(pred.predicted_value - outcome.actual_value)
                error_pct = (
                    (error / outcome.actual_value * 100)
                    if outcome.actual_value != 0
                    else 0.0
                )

                within_bounds: bool | None = None
                if (
                    pred.predicted_lower is not None
                    and pred.predicted_upper is not None
                ):
                    within_bounds = (
                        pred.predicted_lower
                        <= outcome.actual_value
                        <= pred.predicted_upper
                    )
                    if within_bounds:
                        report.predictions_within_bounds += 1

                result = CalibrationComparison(
                    signal_id=pred.signal_id,
                    metric_name=pred.metric_name,
                    predicted=pred.predicted_value,
                    actual=outcome.actual_value,
                    error=error,
                    error_percent=error_pct,
                    within_bounds=within_bounds,
                )
                results.append(result)

                report.total_predictions += 1
                report.errors_by_metric[pred.metric_name].append(error_pct)

        if results:
            report.mean_absolute_error = sum(r.error for r in results) / len(
                results
            )
            report.mean_absolute_percent_error = sum(
                r.error_percent for r in results
            ) / len(results)

        return results, report
