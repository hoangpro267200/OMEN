"""
Anomaly Detection Validation.

Detects suspicious patterns that may indicate manipulation or low-quality signals.
"""

from dataclasses import dataclass
from datetime import datetime, timezone

from ...models.raw_signal import RawSignalEvent
from ...models.validated_signal import ValidationResult
from ...models.common import ValidationStatus
from ...models.explanation import ExplanationStep
from ..base import Rule


@dataclass(frozen=True)
class AnomalyConfig:
    """Thresholds for anomaly detection. Immutable."""

    min_probability: float = 0.05  # Too extreme = suspicious
    max_probability: float = 0.95
    max_probability_change_24h: float = 0.5  # >50% change = suspicious
    min_volume_for_high_confidence: float = 10000.0
    min_traders: int = 10


class AnomalyDetectionRule(Rule[RawSignalEvent, ValidationResult]):
    """
    Detects anomalies that suggest manipulation or unreliable data.

    Checks:
    1. Extreme probabilities (too close to 0 or 1)
    2. Unusual probability movements (too fast)
    3. Low trader count relative to volume
    4. Suspicious patterns
    """

    def __init__(self, config: AnomalyConfig | None = None):
        self._config = config or AnomalyConfig()

    @property
    def name(self) -> str:
        return "anomaly_detection"

    @property
    def version(self) -> str:
        return "2.0.0"

    def apply(self, input_data: RawSignalEvent) -> ValidationResult:
        """Detect anomalies."""
        anomalies: list[str] = []
        risk_score = 0.0

        # Check extreme probability
        prob = input_data.probability
        if prob < self._config.min_probability:
            anomalies.append(f"Probability too low ({prob:.1%})")
            risk_score += 0.3
        elif prob > self._config.max_probability:
            anomalies.append(f"Probability too high ({prob:.1%})")
            risk_score += 0.3

        # Check probability movement
        if input_data.movement:
            if abs(input_data.movement.delta) > self._config.max_probability_change_24h:
                anomalies.append(
                    f"Unusual probability change "
                    f"({input_data.movement.delta:+.1%} in "
                    f"{input_data.movement.window_hours}h)"
                )
                risk_score += 0.4

        # Check trader concentration
        market = input_data.market
        if market.num_traders is not None and market.num_traders < self._config.min_traders:
            if market.total_volume_usd > self._config.min_volume_for_high_confidence:
                anomalies.append(
                    f"High volume (${market.total_volume_usd:,.0f}) "
                    f"but few traders ({market.num_traders})"
                )
                risk_score += 0.3

        # Determine result
        if risk_score >= 0.5:
            return ValidationResult(
                rule_name=self.name,
                rule_version=self.version,
                status=ValidationStatus.REJECTED_MANIPULATION_SUSPECTED,
                score=1.0 - risk_score,
                reason=f"Anomalies detected: {'; '.join(anomalies)}",
            )
        elif anomalies:
            return ValidationResult(
                rule_name=self.name,
                rule_version=self.version,
                status=ValidationStatus.PASSED,
                score=1.0 - risk_score,
                reason=f"Minor anomalies noted: {'; '.join(anomalies)}",
            )
        else:
            return ValidationResult(
                rule_name=self.name,
                rule_version=self.version,
                status=ValidationStatus.PASSED,
                score=1.0,
                reason="No anomalies detected",
            )

    def explain(
        self,
        input_data: RawSignalEvent,
        output_data: ValidationResult,
        processing_time: datetime | None = None,
    ) -> ExplanationStep:
        """Generate explanation for this validation."""
        ts = processing_time or datetime.now(timezone.utc)
        return ExplanationStep(
            step_id=1,
            rule_name=self.name,
            rule_version=self.version,
            input_summary={
                "probability": input_data.probability,
                "has_movement": input_data.movement is not None,
                "num_traders": input_data.market.num_traders,
            },
            output_summary={
                "status": output_data.status.value,
                "score": output_data.score,
                "reason": output_data.reason,
            },
            reasoning=output_data.reason,
            confidence_contribution=output_data.score * 0.2,
            timestamp=ts,
        )
