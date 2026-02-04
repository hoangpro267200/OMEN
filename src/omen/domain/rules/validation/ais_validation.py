"""
AIS validation rules.

Validates AIS signals (port congestion, chokepoint delays) before
they become OMEN signals.

✅ Updated: Now compatible with Rule interface (apply, explain methods).
"""

from typing import Any
from datetime import datetime, timezone

from omen.application.ports.time_provider import utc_now
from omen.domain.rules.base import Rule
from omen.domain.models.raw_signal import RawSignalEvent
from omen.domain.models.validated_signal import ValidationResult
from omen.domain.models.common import ValidationStatus
from omen.domain.models.explanation import ExplanationStep


class AISValidationRuleMixin:
    """Mixin providing apply and explain methods for AIS rules."""
    
    def apply(self, input_data: RawSignalEvent) -> ValidationResult:
        """Apply the rule to input data."""
        result = self.evaluate(input_data)
        
        if result.get("passed", True):
            status = ValidationStatus.PASSED
        else:
            status = ValidationStatus.REJECTED_RULE
        
        return ValidationResult(
            rule_name=self.name,
            rule_version=self.version,
            status=status,
            score=result.get("score", 0.0),
            reason=result.get("reason") or f"{self.name} validation passed",
        )
    
    def explain(
        self,
        input_data: RawSignalEvent,
        output_data: ValidationResult,
        processing_time: datetime | None = None,
    ) -> ExplanationStep:
        """Generate explanation for this rule."""
        return ExplanationStep(
            step_id=1,
            rule_name=self.name,
            rule_version=self.version,
            input_summary={"source": input_data.market.source, "event_id": input_data.event_id},
            output_summary={"status": output_data.status.value, "score": output_data.score},
            reasoning=output_data.reason or self.description,
            confidence_contribution=output_data.score,
            timestamp=processing_time or utc_now(),
        )


class PortCongestionValidationRule(AISValidationRuleMixin, Rule):
    """
    Validate port congestion signals.

    Ensures congestion ratio meets threshold and data is fresh.
    """

    rule_type = "validation"
    description = "Validates port congestion signals meet minimum threshold"
    category = "ais"
    applicable_signal_types = ["disruption"]

    def __init__(self, min_congestion_ratio: float = 1.5):
        self.min_congestion_ratio = min_congestion_ratio
    
    @property
    def name(self) -> str:
        return "port_congestion_validation"
    
    @property
    def version(self) -> str:
        return "1.0.0"

    def evaluate(self, event: RawSignalEvent) -> dict[str, Any]:
        """
        Evaluate port congestion signal.

        Returns:
            dict with keys: passed, score, reason, metadata
        """
        # Only apply to AIS port events
        if event.market.source != "ais":
            return self._skip_result()

        metrics = event.source_metrics or {}
        if "port_code" not in metrics:
            return self._skip_result()

        congestion_ratio = metrics.get("congestion_ratio", 0.0)

        # Check threshold
        passed = congestion_ratio >= self.min_congestion_ratio

        # Score: 1.5x → 0.5, 3x → 1.0
        score = min((congestion_ratio - 1.0) / 2.0, 1.0)
        score = max(0.0, score)

        reason = None
        if not passed:
            reason = (
                f"Congestion ratio {congestion_ratio:.1f}x < threshold {self.min_congestion_ratio}x"
            )

        return {
            "passed": passed,
            "score": score,
            "reason": reason,
            "metadata": {
                "congestion_ratio": congestion_ratio,
                "threshold": self.min_congestion_ratio,
                "port_code": metrics.get("port_code"),
            },
        }

    def _skip_result(self) -> dict[str, Any]:
        return {
            "passed": True,  # Don't block non-AIS events
            "score": 0.0,
            "reason": "Not applicable (non-AIS event)",
            "metadata": {"skipped": True},
        }


class ChokePointDelayValidationRule(AISValidationRuleMixin, Rule):
    """
    Validate chokepoint delay signals.

    Ensures delay ratio meets threshold.
    """

    rule_type = "validation"
    description = "Validates chokepoint delay signals meet minimum threshold"
    category = "ais"
    applicable_signal_types = ["disruption"]

    def __init__(self, min_delay_ratio: float = 1.5):
        self.min_delay_ratio = min_delay_ratio
    
    @property
    def name(self) -> str:
        return "chokepoint_delay_validation"
    
    @property
    def version(self) -> str:
        return "1.0.0"

    def evaluate(self, event: RawSignalEvent) -> dict[str, Any]:
        """Evaluate chokepoint delay signal."""
        if event.market.source != "ais":
            return self._skip_result()

        metrics = event.source_metrics or {}

        # Check if this is a chokepoint event
        if "delay_ratio" not in metrics:
            return self._skip_result()

        delay_ratio = metrics.get("delay_ratio", 0.0)
        blockage = metrics.get("blockage_detected", False)

        # Blockage always passes
        if blockage:
            return {
                "passed": True,
                "score": 1.0,
                "reason": None,
                "metadata": {
                    "delay_ratio": delay_ratio,
                    "blockage_detected": True,
                },
            }

        # Check threshold
        passed = delay_ratio >= self.min_delay_ratio
        score = min((delay_ratio - 1.0) / 1.0, 1.0)
        score = max(0.0, score)

        reason = None
        if not passed:
            reason = f"Delay ratio {delay_ratio:.1f}x < threshold {self.min_delay_ratio}x"

        return {
            "passed": passed,
            "score": score,
            "reason": reason,
            "metadata": {
                "delay_ratio": delay_ratio,
                "threshold": self.min_delay_ratio,
            },
        }

    def _skip_result(self) -> dict[str, Any]:
        return {
            "passed": True,
            "score": 0.0,
            "reason": "Not applicable",
            "metadata": {"skipped": True},
        }


class AISDataFreshnessRule(AISValidationRuleMixin, Rule):
    """
    Validate AIS data freshness.

    AIS data should be recent (< 1 hour old by default).
    """

    rule_type = "validation"
    description = "Ensures AIS data is fresh (not stale)"
    category = "ais"
    applicable_signal_types = ["disruption"]

    def __init__(self, max_age_hours: float = 1.0):
        self.max_age_hours = max_age_hours
    
    @property
    def name(self) -> str:
        return "ais_data_freshness"
    
    @property
    def version(self) -> str:
        return "1.0.0"

    def evaluate(self, event: RawSignalEvent) -> dict[str, Any]:
        """Evaluate data freshness."""
        if event.market.source != "ais":
            return self._skip_result()

        # Check data timestamp
        # FIX: Use market_last_updated (on RawSignalEvent) or market.created_at
        # Note: MarketMetadata does NOT have last_trade_at field
        last_update = event.market_last_updated or event.market.created_at
        if not last_update:
            return {
                "passed": False,
                "score": 0.0,
                "reason": "No timestamp available",
                "metadata": {"age_hours": None},
            }

        now = utc_now()

        # Ensure timezone-aware comparison
        if last_update.tzinfo is None:
            last_update = last_update.replace(tzinfo=timezone.utc)

        age_hours = (now - last_update).total_seconds() / 3600

        passed = age_hours <= self.max_age_hours

        # Score: fresh data = 1.0, decays linearly
        score = max(1.0 - (age_hours / (self.max_age_hours * 2)), 0.0)

        reason = None
        if not passed:
            reason = f"Data is {age_hours:.1f}h old (max: {self.max_age_hours}h)"

        return {
            "passed": passed,
            "score": score,
            "reason": reason,
            "metadata": {
                "age_hours": age_hours,
                "max_age_hours": self.max_age_hours,
            },
        }

    def _skip_result(self) -> dict[str, Any]:
        return {
            "passed": True,
            "score": 0.0,
            "reason": "Not applicable",
            "metadata": {"skipped": True},
        }


class AISDataQualityRule(AISValidationRuleMixin, Rule):
    """
    Validate AIS data quality score.

    Checks the data_quality field from source.
    """

    rule_type = "validation"
    description = "Validates AIS data quality meets minimum threshold"
    category = "ais"
    applicable_signal_types = ["disruption"]

    def __init__(self, min_quality: float = 0.7):
        self.min_quality = min_quality
    
    @property
    def name(self) -> str:
        return "ais_data_quality"
    
    @property
    def version(self) -> str:
        return "1.0.0"

    def evaluate(self, event: RawSignalEvent) -> dict[str, Any]:
        """Evaluate data quality."""
        if event.market.source != "ais":
            return self._skip_result()

        metrics = event.source_metrics or {}
        quality = metrics.get("data_quality", 1.0)

        passed = quality >= self.min_quality
        score = quality

        reason = None
        if not passed:
            reason = f"Data quality {quality:.2f} < threshold {self.min_quality:.2f}"

        return {
            "passed": passed,
            "score": score,
            "reason": reason,
            "metadata": {
                "data_quality": quality,
                "threshold": self.min_quality,
            },
        }

    def _skip_result(self) -> dict[str, Any]:
        return {
            "passed": True,
            "score": 0.0,
            "reason": "Not applicable",
            "metadata": {"skipped": True},
        }
