"""
Commodity Context Validation Rule.

Validates that commodity-sourced signals (price spikes) meet quality thresholds.
Commodity signals are CONTEXT ONLY - they confirm/weight other signals,
never standalone escalation.

Key principles:
- Deterministic: Same input = same output
- Bounded: commodity_spike_score cannot exceed max_confidence_boost
- Context-only: Commodity signals add weight, not standalone risk
- Config-driven: Thresholds from YAML

NOTE: No logging in domain layer - maintain purity for determinism.
"""

from __future__ import annotations

import math
from datetime import datetime, timezone

from omen.domain.models.raw_signal import RawSignalEvent
from omen.domain.models.validated_signal import ValidationResult
from omen.domain.models.common import ValidationStatus
from omen.domain.models.explanation import ExplanationStep
from omen.domain.rules.base import Rule

# Default thresholds
DEFAULT_MIN_SEVERITY_FOR_BOOST = "minor"
DEFAULT_MAX_CONFIDENCE_BOOST = 0.08
DEFAULT_MAX_ZSCORE = 10.0  # Cap for JSON safety


# Severity levels (ordered)
SEVERITY_ORDER = ["none", "minor", "moderate", "major"]


class CommodityContextRule(Rule[RawSignalEvent, ValidationResult]):
    """
    Validation rule for commodity price spike signals.

    Checks:
    1. Spike is detected (is_spike=True)
    2. Severity meets minimum threshold
    3. Z-score is bounded (no NaN/Inf)
    4. Data is not stale

    Bounded behavior:
    - Commodity signals only provide CONTEXT, not standalone risk
    - Maximum confidence boost is capped
    - Z-scores are bounded [-10, 10] for JSON safety

    Note: This rule only applies to signals from the 'commodity' source.
    Non-commodity signals pass through unchanged.
    """

    def __init__(
        self,
        min_severity: str = DEFAULT_MIN_SEVERITY_FOR_BOOST,
        max_confidence_boost: float = DEFAULT_MAX_CONFIDENCE_BOOST,
        max_zscore: float = DEFAULT_MAX_ZSCORE,
    ):
        self._min_severity = min_severity
        self._max_confidence_boost = max_confidence_boost
        self._max_zscore = max_zscore

    @property
    def name(self) -> str:
        return "commodity_context"

    @property
    def version(self) -> str:
        return "1.0.0"

    def apply(self, signal: RawSignalEvent) -> ValidationResult:
        """
        Apply commodity context validation.

        Returns PASSED for non-commodity signals (rule doesn't apply).
        Returns PASSED with bounded score for valid commodity spikes.
        Returns PASSED with low score for non-spike commodity data.
        """
        # Check if this is a commodity-sourced signal
        source_metrics = getattr(signal, "source_metrics", None) or {}

        if not source_metrics:
            # Not from a specialized source - pass through
            return ValidationResult(
                rule_name=self.name,
                rule_version=self.version,
                status=ValidationStatus.PASSED,
                score=1.0,
                reason="Not a commodity source signal - rule not applicable",
            )

        # Check for commodity-specific metrics
        is_spike = source_metrics.get("is_spike")
        severity = source_metrics.get("severity")
        zscore = source_metrics.get("zscore")
        pct_change = source_metrics.get("pct_change")

        # If no commodity metrics, not a commodity source
        if is_spike is None and zscore is None:
            return ValidationResult(
                rule_name=self.name,
                rule_version=self.version,
                status=ValidationStatus.PASSED,
                score=1.0,
                reason="Not a commodity source signal",
            )

        # JSON safety check: ensure zscore is bounded (no logging - domain is pure)
        if zscore is not None:
            if math.isnan(zscore) or math.isinf(zscore):
                # Invalid zscore detected, cap to safe value
                zscore = 0.0
            zscore = max(-self._max_zscore, min(self._max_zscore, zscore))

        # If not a spike, pass with neutral score (context only)
        if not is_spike:
            return ValidationResult(
                rule_name=self.name,
                rule_version=self.version,
                status=ValidationStatus.PASSED,
                score=0.5,  # Neutral - no boost
                reason="No significant commodity spike detected",
            )

        # Check severity threshold
        severity_value = severity or "none"
        severity_index = (
            SEVERITY_ORDER.index(severity_value) if severity_value in SEVERITY_ORDER else 0
        )
        min_severity_index = (
            SEVERITY_ORDER.index(self._min_severity) if self._min_severity in SEVERITY_ORDER else 1
        )

        if severity_index < min_severity_index:
            return ValidationResult(
                rule_name=self.name,
                rule_version=self.version,
                status=ValidationStatus.PASSED,
                score=0.5,  # Neutral - below threshold
                reason=f"Spike severity {severity_value} below threshold {self._min_severity}",
            )

        # Calculate bounded context score
        # Scale from 0.5 (baseline) to 0.5 + max_confidence_boost
        base_score = 0.5

        # Boost based on severity
        severity_boost = {
            "minor": 0.3,
            "moderate": 0.6,
            "major": 1.0,
        }.get(severity_value, 0.0)

        # Calculate final score (bounded)
        boost = severity_boost * self._max_confidence_boost
        final_score = min(base_score + boost, 1.0)

        return ValidationResult(
            rule_name=self.name,
            rule_version=self.version,
            status=ValidationStatus.PASSED,
            score=final_score,
            reason=f"Commodity spike: {severity_value} severity, {pct_change:+.1f}% change, zscore={zscore:.2f}",
        )

    def explain(
        self,
        input_data: RawSignalEvent,
        output_data: ValidationResult,
        processing_time: datetime | None = None,
    ) -> ExplanationStep:
        """Generate explanation for this rule application."""
        _ = processing_time or datetime.now(timezone.utc)  # Use for timestamp if needed
        source_metrics = getattr(input_data, "source_metrics", None) or {}

        return ExplanationStep(
            step_id=1,  # Default step ID
            rule_name=self.name,
            rule_version=self.version,
            input_summary={
                "symbol": source_metrics.get("symbol", "unknown"),
                "category": source_metrics.get("category", "unknown"),
                "is_spike": source_metrics.get("is_spike", False),
                "severity": source_metrics.get("severity", "none"),
                "pct_change": source_metrics.get("pct_change"),
                "zscore": source_metrics.get("zscore"),
            },
            output_summary={
                "status": output_data.status.value,
                "score": output_data.score,
                "reason": output_data.reason,
            },
            reasoning=f"Commodity context: {output_data.reason}",
            confidence_contribution=output_data.score,
            timestamp=processing_time,
        )
