"""
News Quality Gate Validation Rule.

Validates that news-sourced signals meet quality thresholds.
Implements FAIL-CLOSED principle: low-quality news is rejected,
not escalated.

Key principles:
- Deterministic: Same input + context = same output
- Fail-closed: Uncertain/low-quality → REJECT
- Bounded: news_score cannot exceed max_confidence_boost
- Config-driven: Thresholds from YAML

NOTE: No logging in domain layer - maintain purity for determinism.
"""

from __future__ import annotations

from datetime import datetime, timezone

from omen.domain.models.raw_signal import RawSignalEvent
from omen.domain.models.validated_signal import ValidationResult
from omen.domain.models.common import ValidationStatus
from omen.domain.models.explanation import ExplanationStep
from omen.domain.rules.base import Rule

# Default thresholds (can be overridden by config)
DEFAULT_MIN_CREDIBILITY = 0.3
DEFAULT_MIN_RECENCY = 0.1
DEFAULT_MIN_COMBINED_SCORE = 0.2
DEFAULT_MAX_CONFIDENCE_BOOST = 0.10


class NewsQualityGateRule(Rule[RawSignalEvent, ValidationResult]):
    """
    Validation rule for news-sourced signals.

    Checks:
    1. Source credibility meets threshold
    2. Recency score meets threshold (not stale)
    3. Combined quality score meets threshold
    4. Not a duplicate

    Fail-closed behavior:
    - If source_metrics missing → PASS (not a news source)
    - If credibility/recency below threshold → REJECT
    - If quality score below threshold → REJECT
    - If duplicate → REJECT

    Note: This rule only applies to signals from the 'news' source.
    Non-news signals pass through unchanged.
    """

    def __init__(
        self,
        min_credibility: float = DEFAULT_MIN_CREDIBILITY,
        min_recency: float = DEFAULT_MIN_RECENCY,
        min_combined_score: float = DEFAULT_MIN_COMBINED_SCORE,
        max_confidence_boost: float = DEFAULT_MAX_CONFIDENCE_BOOST,
    ):
        self._min_credibility = min_credibility
        self._min_recency = min_recency
        self._min_combined_score = min_combined_score
        self._max_confidence_boost = max_confidence_boost

    @property
    def name(self) -> str:
        return "news_quality_gate"

    @property
    def version(self) -> str:
        return "1.0.0"

    def apply(self, signal: RawSignalEvent) -> ValidationResult:
        """
        Apply news quality gate validation.

        Returns PASSED for non-news signals (rule doesn't apply).
        Returns PASSED/REJECTED for news signals based on quality.
        """
        # Check if this is a news-sourced signal
        source_metrics = getattr(signal, "source_metrics", None) or {}

        if not source_metrics:
            # Not from a specialized source - pass through
            return ValidationResult(
                rule_name=self.name,
                rule_version=self.version,
                status=ValidationStatus.PASSED,
                score=1.0,
                reason="Not a news source signal - rule not applicable",
            )

        # Check for news-specific metrics
        credibility = source_metrics.get("credibility_score")
        recency = source_metrics.get("recency_score")
        combined = source_metrics.get("combined_score")
        is_duplicate = source_metrics.get("is_duplicate", False)

        # If no news metrics, not a news source
        if credibility is None and recency is None:
            return ValidationResult(
                rule_name=self.name,
                rule_version=self.version,
                status=ValidationStatus.PASSED,
                score=1.0,
                reason="Not a news source signal",
            )

        # FAIL-CLOSED checks
        if is_duplicate:
            return ValidationResult(
                rule_name=self.name,
                rule_version=self.version,
                status=ValidationStatus.REJECTED_RULE,
                score=0.0,
                reason="Duplicate news article detected",
            )

        if credibility is not None and credibility < self._min_credibility:
            return ValidationResult(
                rule_name=self.name,
                rule_version=self.version,
                status=ValidationStatus.REJECTED_RULE,
                score=credibility,
                reason=f"News credibility too low: {credibility:.2f} < {self._min_credibility}",
            )

        if recency is not None and recency < self._min_recency:
            return ValidationResult(
                rule_name=self.name,
                rule_version=self.version,
                status=ValidationStatus.REJECTED_RULE,
                score=recency,
                reason=f"News too stale: recency={recency:.2f} < {self._min_recency}",
            )

        if combined is not None and combined < self._min_combined_score:
            return ValidationResult(
                rule_name=self.name,
                rule_version=self.version,
                status=ValidationStatus.REJECTED_RULE,
                score=combined,
                reason=f"Combined news quality too low: {combined:.2f} < {self._min_combined_score}",
            )

        # Calculate bounded news quality score
        # Score contributes to confidence but is bounded
        quality_score = (
            combined
            if combined is not None
            else ((credibility or 0.5) * 0.6 + (recency or 0.5) * 0.4)
        )

        # Bound the contribution
        bounded_score = (
            min(quality_score, 1.0 - self._max_confidence_boost) + self._max_confidence_boost
        )

        return ValidationResult(
            rule_name=self.name,
            rule_version=self.version,
            status=ValidationStatus.PASSED,
            score=bounded_score,
            reason=f"News quality passed: credibility={credibility:.2f}, recency={recency:.2f}",
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
                "source": source_metrics.get("source_domain", "unknown"),
                "credibility": source_metrics.get("credibility_score"),
                "recency": source_metrics.get("recency_score"),
                "is_duplicate": source_metrics.get("is_duplicate", False),
                "matched_topics": source_metrics.get("matched_topics", []),
            },
            output_summary={
                "status": output_data.status.value,
                "score": output_data.score,
                "reason": output_data.reason,
            },
            reasoning=f"News quality gate: {output_data.reason}",
            confidence_contribution=(
                output_data.score if output_data.status == ValidationStatus.PASSED else 0.0
            ),
            timestamp=processing_time,
        )
