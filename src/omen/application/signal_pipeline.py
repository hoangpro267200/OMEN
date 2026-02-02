"""
OMEN Signal-Only Pipeline.

Stages: Validate → Enrich → Generate (OmenSignal).

No impact translation. Impact assessment is RiskCast's responsibility.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from ..domain.models.common import RulesetVersion
from ..domain.models.context import ProcessingContext
from ..domain.models.raw_signal import RawSignalEvent
from ..domain.models.omen_signal import OmenSignal
from ..domain.services.signal_validator import SignalValidator, ValidationOutcome
from ..domain.services.signal_enricher import SignalEnricher
from ..infrastructure.debug.rejection_tracker import get_rejection_tracker


@dataclass
class SignalProcessingResult:
    """Result of processing an event in the signal-only pipeline."""

    success: bool
    signal: Optional[OmenSignal] = None
    rejection_stage: Optional[str] = None
    rejection_reason: Optional[str] = None


class SignalOnlyPipeline:
    """
    Signal-only OMEN pipeline.

    Produces OmenSignal (structured intelligence) only.
    No impact calculations, no recommendations.
    """

    def __init__(
        self,
        validator: SignalValidator,
        enricher: SignalEnricher,
        ruleset_version: RulesetVersion | None = None,
    ):
        self._validator = validator
        self._enricher = enricher
        self._ruleset_version = ruleset_version or RulesetVersion("1.0.0")
        self._tracker = get_rejection_tracker()

    def process(
        self,
        event: RawSignalEvent,
        context: ProcessingContext | None = None,
    ) -> SignalProcessingResult:
        """
        Process a single event: validate → enrich → generate OmenSignal.

        Returns SignalProcessingResult with signal on success,
        or rejection_stage/rejection_reason on failure.
        """
        ctx = context or ProcessingContext.create(self._ruleset_version)

        # === STAGE 1: VALIDATION ===
        outcome: ValidationOutcome = self._validator.validate(event, context=ctx)

        if not outcome.passed:
            self._tracker.record_rejection(
                event_id=str(event.event_id),
                stage="validation",
                reason=outcome.rejection_reason or "unknown",
                title=event.title,
                probability=event.probability,
                liquidity=event.market.current_liquidity_usd,
                rule_name=outcome.results[0].rule_name if outcome.results else None,
                rule_version=outcome.results[0].rule_version if outcome.results else None,
            )
            return SignalProcessingResult(
                success=False,
                rejection_stage="validation",
                rejection_reason=outcome.rejection_reason,
            )

        validated_signal = outcome.signal
        if validated_signal is None:
            return SignalProcessingResult(
                success=False,
                rejection_stage="validation",
                rejection_reason="No validated signal",
            )

        # Build validation context for enricher
        validation_context: dict = {
            "confidence_factors": {
                "liquidity": validated_signal.liquidity_score,
                "geographic": next(
                    (
                        r.score
                        for r in validated_signal.validation_results
                        if r.rule_name == "geographic_relevance"
                    ),
                    0.5,
                ),
                "source_reliability": 0.85,
            },
            "validation_results": validated_signal.validation_results,
        }

        # === STAGE 2: ENRICHMENT ===
        enrichment = self._enricher.enrich(event, validation_context)

        # === STAGE 3: SIGNAL GENERATION ===
        try:
            signal = OmenSignal.from_validated_event(validated_signal, enrichment)
        except Exception as e:
            self._tracker.record_rejection(
                event_id=str(event.event_id),
                stage="generation",
                reason=str(e),
                title=event.title,
            )
            return SignalProcessingResult(
                success=False,
                rejection_stage="generation",
                rejection_reason=str(e),
            )

        self._tracker.record_passed(
            signal_id=signal.signal_id,
            event_id=str(event.event_id),
            title=signal.title,
            probability=signal.probability,
            confidence=signal.confidence_score,
            confidence_level=signal.confidence_level.value,
            metrics_count=0,
            routes_count=0,
        )

        return SignalProcessingResult(success=True, signal=signal)

    def process_batch(
        self,
        events: list[RawSignalEvent],
        context: ProcessingContext | None = None,
    ) -> list[SignalProcessingResult]:
        """Process multiple events through the signal-only pipeline."""
        ctx = context or ProcessingContext.create(self._ruleset_version)
        return [self.process(evt, context=ctx) for evt in events]
