"""
Anomaly Detection Validation.

Detects suspicious patterns that may indicate manipulation or low-quality signals.
Includes statistical Z-score based detection for numerical anomalies.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional
import statistics

from omen.application.ports.time_provider import utc_now
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
    z_score_threshold: float = 3.0  # Standard deviations for anomaly


@dataclass
class ZScoreResult:
    """Result of Z-score anomaly detection."""
    
    is_anomaly: bool
    z_score: float
    threshold: float
    details: str


class StatisticalAnomalyDetector:
    """
    Z-score based anomaly detection for numerical values.
    
    Maintains a sliding window of historical values to compute
    mean and standard deviation for anomaly detection.
    """
    
    def __init__(self, z_threshold: float = 3.0, max_history: int = 1000):
        """
        Initialize detector.
        
        Args:
            z_threshold: Number of standard deviations for anomaly (default 3.0)
            max_history: Maximum historical observations to keep
        """
        self._z_threshold = z_threshold
        self._max_history = max_history
        self._history: List[float] = []
    
    def add_observation(self, value: float) -> None:
        """Add a new observation to history."""
        self._history.append(value)
        if len(self._history) > self._max_history:
            self._history.pop(0)
    
    def detect(self, value: float) -> ZScoreResult:
        """
        Detect if value is an anomaly using z-score.
        
        Args:
            value: Value to check
            
        Returns:
            ZScoreResult with detection details
        """
        if len(self._history) < 10:
            # Not enough history for statistical detection
            return ZScoreResult(
                is_anomaly=False,
                z_score=0.0,
                threshold=self._z_threshold,
                details="Insufficient history for Z-score detection (need 10+ observations)"
            )
        
        mean = statistics.mean(self._history)
        stdev = statistics.stdev(self._history)
        
        if stdev == 0:
            return ZScoreResult(
                is_anomaly=False,
                z_score=0.0,
                threshold=self._z_threshold,
                details="Zero standard deviation - all values identical"
            )
        
        z_score = abs((value - mean) / stdev)
        is_anomaly = z_score > self._z_threshold
        
        return ZScoreResult(
            is_anomaly=is_anomaly,
            z_score=round(z_score, 4),
            threshold=self._z_threshold,
            details=f"Z-score: {z_score:.2f}, Mean: {mean:.4f}, StdDev: {stdev:.4f}"
        )
    
    def detect_with_range(
        self,
        value: float,
        min_valid: Optional[float] = None,
        max_valid: Optional[float] = None
    ) -> ZScoreResult:
        """
        Detect anomalies with combined Z-score and range check.
        
        Args:
            value: Value to check
            min_valid: Minimum valid value (hard boundary)
            max_valid: Maximum valid value (hard boundary)
        """
        # Check hard boundaries first
        if min_valid is not None and value < min_valid:
            return ZScoreResult(
                is_anomaly=True,
                z_score=float('inf'),
                threshold=self._z_threshold,
                details=f"Value {value:.4f} below minimum valid {min_valid}"
            )
        
        if max_valid is not None and value > max_valid:
            return ZScoreResult(
                is_anomaly=True,
                z_score=float('inf'),
                threshold=self._z_threshold,
                details=f"Value {value:.4f} above maximum valid {max_valid}"
            )
        
        # Then do statistical check
        return self.detect(value)


# Global detectors for different metrics
_probability_detector = StatisticalAnomalyDetector(z_threshold=3.0)
_volume_detector = StatisticalAnomalyDetector(z_threshold=3.0)
_price_change_detector = StatisticalAnomalyDetector(z_threshold=2.5)


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
        """Detect anomalies using rules and statistical Z-score."""
        anomalies: list[str] = []
        risk_score = 0.0

        # Check extreme probability (hard boundaries)
        prob = input_data.probability
        if prob < self._config.min_probability:
            anomalies.append(f"Probability too low ({prob:.1%})")
            risk_score += 0.3
        elif prob > self._config.max_probability:
            anomalies.append(f"Probability too high ({prob:.1%})")
            risk_score += 0.3

        # Z-score based probability anomaly detection
        z_result = _probability_detector.detect_with_range(
            prob,
            min_valid=0.0,
            max_valid=1.0
        )
        _probability_detector.add_observation(prob)  # Add to history
        
        if z_result.is_anomaly and z_result.z_score != float('inf'):
            anomalies.append(f"Statistical anomaly: {z_result.details}")
            risk_score += 0.2

        # Check probability movement
        if input_data.movement:
            if abs(input_data.movement.delta) > self._config.max_probability_change_24h:
                anomalies.append(
                    f"Unusual probability change "
                    f"({input_data.movement.delta:+.1%} in "
                    f"{input_data.movement.window_hours}h)"
                )
                risk_score += 0.4
            
            # Z-score check for price/probability changes
            change_z = _price_change_detector.detect(abs(input_data.movement.delta))
            _price_change_detector.add_observation(abs(input_data.movement.delta))
            
            if change_z.is_anomaly:
                anomalies.append(f"Change rate anomaly: {change_z.details}")
                risk_score += 0.15

        # Check trader concentration
        market = input_data.market
        if market.num_traders is not None and market.num_traders < self._config.min_traders:
            if market.total_volume_usd > self._config.min_volume_for_high_confidence:
                anomalies.append(
                    f"High volume (${market.total_volume_usd:,.0f}) "
                    f"but few traders ({market.num_traders})"
                )
                risk_score += 0.3

        # Z-score based volume anomaly detection
        if market.total_volume_usd:
            vol_z = _volume_detector.detect(market.total_volume_usd)
            _volume_detector.add_observation(market.total_volume_usd)
            
            if vol_z.is_anomaly:
                anomalies.append(f"Volume anomaly: {vol_z.details}")
                risk_score += 0.15

        # Determine result
        if risk_score >= 0.5:
            return ValidationResult(
                rule_name=self.name,
                rule_version=self.version,
                status=ValidationStatus.REJECTED_MANIPULATION_SUSPECTED,
                score=max(0.0, 1.0 - risk_score),
                reason=f"Anomalies detected: {'; '.join(anomalies)}",
            )
        elif anomalies:
            return ValidationResult(
                rule_name=self.name,
                rule_version=self.version,
                status=ValidationStatus.PASSED,
                score=max(0.0, 1.0 - risk_score),
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
        ts = processing_time or utc_now()
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
