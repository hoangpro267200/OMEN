"""
Layer 2 orchestration: Signal validation service.

NOTE: No logging in domain layer - errors are captured in ValidationOutcome.
"""

from dataclasses import dataclass
from typing import List

from omen.domain.models.raw_signal import RawSignalEvent
from omen.domain.models.validated_signal import ValidatedSignal, ValidationResult
from omen.domain.models.common import (
    SignalCategory,
    ValidationStatus,
    RulesetVersion,
    generate_deterministic_hash,
)
from omen.domain.models.context import ProcessingContext
from omen.domain.models.explanation import ExplanationChain, ExplanationStep
from omen.domain.rules.base import Rule
from omen.domain.rules.validation.liquidity_rule import LiquidityValidationRule
from omen.domain.rules.validation.geographic_relevance_rule import (
    GeographicRelevanceRule,
)
from omen.domain.rules.validation.semantic_relevance_rule import (
    SemanticRelevanceRule,
)
from omen.domain.rules.validation.anomaly_detection_rule import (
    AnomalyDetectionRule,
)


@dataclass(frozen=True)
class ValidationOutcome:
    """Result of validation: either a valid signal or rejection with reasons. Immutable."""

    passed: bool
    signal: ValidatedSignal | None
    rejection_reason: str | None = None
    results: tuple[ValidationResult, ...] | None = None  # Changed to tuple for immutability


class ValidationFailure(Exception):
    """Raised when validation fails (legacy; prefer ValidationOutcome)."""

    def __init__(self, result: ValidationResult, reason: str):
        self.result = result
        self.reason = reason
        super().__init__(reason)


class SignalValidator:
    """
    Multi-layer signal validation.

    Default rule order:
    1. Liquidity (fast, cheap — filter obvious noise first)
    2. Anomaly (detect manipulation before semantic analysis)
    3. Semantic (keyword relevance)
    4. Geographic (location relevance)
    """

    def __init__(self, rules: List[Rule], fail_on_rule_error: bool = True):
        """
        Initialize signal validator.

        Args:
            rules: List of validation rules to apply
            fail_on_rule_error: If True, stop and reject on first rule exception.
                If False, log the error, record REJECTED_RULE_ERROR, and continue.
        """
        self.rules = rules
        self._fail_on_rule_error = fail_on_rule_error

    @classmethod
    def create_default(cls) -> "SignalValidator":
        """Create validator with all standard rules."""
        return cls(
            rules=[
                LiquidityValidationRule(min_liquidity_usd=1000.0),
                AnomalyDetectionRule(),
                SemanticRelevanceRule(),
                GeographicRelevanceRule(),
            ],
            fail_on_rule_error=False,
        )

    def validate(
        self,
        signal: RawSignalEvent,
        context: ProcessingContext,
    ) -> ValidationOutcome:
        """
        Validate an event through all registered rules.

        Errors in individual rules are caught and logged;
        the rule is marked as "errored" but processing continues unless
        fail_on_rule_error is True.
        All timestamps derive from context for deterministic replay.
        """
        validation_results: List[ValidationResult] = []
        explanation_chain = ExplanationChain.create(context)

        for i, rule in enumerate(self.rules, start=1):
            try:
                result = rule.apply(signal)
                validation_results.append(result)

                explanation_step = rule.explain(
                    signal, result, processing_time=context.processing_time
                )
                explanation_step = explanation_step.model_copy(update={"step_id": i})
                explanation_chain = explanation_chain.add_step(explanation_step)

                if result.status != ValidationStatus.PASSED:
                    return ValidationOutcome(
                        passed=False,
                        signal=None,
                        rejection_reason=result.reason,
                        results=tuple(validation_results),
                    )
            except Exception as e:
                # Error captured in ValidationResult - no logging in domain layer
                # Application layer should handle logging if needed
                error_result = ValidationResult(
                    rule_name=rule.name,
                    rule_version=rule.version,
                    status=ValidationStatus.REJECTED_RULE_ERROR,
                    score=0.0,
                    reason=f"Rule error: {str(e)}",
                )
                validation_results.append(error_result)
                if self._fail_on_rule_error:
                    return ValidationOutcome(
                        passed=False,
                        signal=None,
                        rejection_reason=f"Rule {rule.name} errored: {e}",
                        results=tuple(validation_results),
                    )

        # All rules passed
        overall_score = (
            sum(r.score for r in validation_results) / len(validation_results)
            if validation_results
            else 0.0
        )
        liquidity_score = next(
            (r.score for r in validation_results if r.rule_name == "liquidity_validation"),
            0.0,
        )
        signal_strength = overall_score
        category = self._infer_category(signal)
        chokepoints = self._extract_chokepoints(signal)
        explanation_chain = explanation_chain.finalize(context)

        validated_signal = ValidatedSignal(
            event_id=signal.event_id,
            original_event=signal,
            category=category,
            relevant_locations=signal.inferred_locations,
            affected_chokepoints=chokepoints,
            validation_results=validation_results,
            overall_validation_score=overall_score,
            signal_strength=signal_strength,
            liquidity_score=liquidity_score,
            explanation=explanation_chain,
            ruleset_version=context.ruleset_version,
            validated_at=context.processing_time,
        )
        return ValidationOutcome(
            passed=True,
            signal=validated_signal,
            results=tuple(validation_results),
        )

    def _infer_category(self, signal: RawSignalEvent) -> SignalCategory:
        """Infer signal category from content."""
        content_lower = (signal.title + " " + (signal.description or "")).lower()
        keywords_lower = [k.lower() for k in signal.keywords]

        if any(
            kw in content_lower or kw in keywords_lower
            for kw in ["war", "conflict", "attack", "geopolitical"]
        ):
            return SignalCategory.GEOPOLITICAL
        if any(kw in content_lower or kw in keywords_lower for kw in ["strike", "labor", "union"]):
            return SignalCategory.LABOR
        if any(
            kw in content_lower or kw in keywords_lower
            for kw in ["port", "canal", "infrastructure", "shipping"]
        ):
            return SignalCategory.INFRASTRUCTURE
        if any(
            kw in content_lower or kw in keywords_lower for kw in ["climate", "weather", "storm"]
        ):
            return SignalCategory.CLIMATE
        if any(
            kw in content_lower or kw in keywords_lower for kw in ["regulation", "policy", "law"]
        ):
            return SignalCategory.REGULATORY
        if any(
            kw in content_lower or kw in keywords_lower for kw in ["economic", "market", "trade"]
        ):
            return SignalCategory.ECONOMIC

        return SignalCategory.UNKNOWN

    def _extract_chokepoints(self, signal: RawSignalEvent) -> List[str]:
        """Extract logistics chokepoints from signal."""
        chokepoints = []
        content_lower = (signal.title + " " + (signal.description or "")).lower()
        keywords_lower = [k.lower() for k in signal.keywords]

        chokepoint_keywords = {
            "suez canal": "Suez Canal",
            "suez": "Suez Canal",
            "red sea": "Red Sea",
            "bab el-mandeb": "Bab el-Mandeb Strait",
            "strait of malacca": "Strait of Malacca",
            "panama canal": "Panama Canal",
        }

        for keyword, chokepoint in chokepoint_keywords.items():
            if keyword in content_lower or keyword in keywords_lower:
                if chokepoint not in chokepoints:
                    chokepoints.append(chokepoint)

        return chokepoints
