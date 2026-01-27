"""OMEN Main Pipeline.

Orchestrates the 4-layer intelligence transformation:
Layer 1 (Signal Sourcing) → Layer 2 (Validation) →
Layer 3 (Impact Translation) → Layer 4 (Output)

The pipeline is:
- Idempotent: Same input → same output
- Explainable: Full audit trail
- Deterministic: No randomness
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Sequence
import logging

from ..domain.models.common import RulesetVersion, ImpactDomain
from ..domain.models.context import ProcessingContext
from ..domain.models.raw_signal import RawSignalEvent
from ..domain.models.validated_signal import ValidatedSignal
from ..domain.models.impact_assessment import ImpactAssessment
from ..domain.models.omen_signal import OmenSignal

from ..domain.services.signal_validator import SignalValidator, ValidationOutcome
from ..domain.services.impact_translator import ImpactTranslator
from ..domain.errors import OmenError, PersistenceError, PublishError

from ..infrastructure.dead_letter import DeadLetterQueue

from .ports.signal_source import SignalSource
from .ports.signal_repository import SignalRepository
from .ports.output_publisher import OutputPublisher
from .dto.pipeline_result import PipelineResult, PipelineStats


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PipelineConfig:
    """Configuration for pipeline execution."""

    ruleset_version: RulesetVersion
    target_domains: frozenset[ImpactDomain]
    min_confidence_for_output: float = 0.3
    enable_dry_run: bool = False
    fail_on_publish_error: bool = False
    enable_dlq: bool = True

    @classmethod
    def default(cls) -> "PipelineConfig":
        return cls(
            ruleset_version=RulesetVersion("v1.0.0"),
            target_domains=frozenset({ImpactDomain.LOGISTICS}),
        )


class OmenPipeline:
    """
    The main OMEN intelligence pipeline.

    Responsible for the four irreversible transformations:
    1. Convert raw prediction market data into credible signals
    2. Eliminate noise, manipulation, and irrelevant events
    3. Translate abstract probabilities into domain-specific impacts
    4. Output structured intelligence objects

    IDEMPOTENCY GUARANTEE:
    Given the same RawSignalEvent (identified by event_id + observed_at),
    the pipeline will produce identical outputs.
    """

    def __init__(
        self,
        validator: SignalValidator,
        translator: ImpactTranslator,
        repository: SignalRepository | None = None,
        publisher: OutputPublisher | None = None,
        dead_letter_queue: DeadLetterQueue | None = None,
        config: PipelineConfig | None = None,
    ):
        self._validator = validator
        self._translator = translator
        self._repository = repository
        self._publisher = publisher
        self._dlq = dead_letter_queue if dead_letter_queue is not None else DeadLetterQueue()
        self._config = config or PipelineConfig.default()

        logger.info(
            "Pipeline initialized with ruleset %s, targeting domains %s",
            self._config.ruleset_version,
            self._config.target_domains,
        )

    def process_single(
        self,
        event: RawSignalEvent,
        context: ProcessingContext | None = None,
    ) -> PipelineResult:
        """
        Process a single raw signal through the full pipeline.

        Args:
            event: The raw signal event.
            context: Processing context. If None, creates a new context.
                Pass explicit context for deterministic replay.

        Errors are caught, logged, and optionally sent to DLQ.
        """
        ctx = context or ProcessingContext.create(self._config.ruleset_version)
        stats = PipelineStats()
        stats.events_received = 1
        logger.info("Processing event: %s", event.event_id)

        try:
            return self._process_single_inner(event, stats, ctx)
        except OmenError as e:
            return self._handle_omen_error(event, e, stats, ctx)
        except Exception as e:
            return self._handle_unexpected_error(event, e, stats, ctx)

    def _process_single_inner(
        self,
        event: RawSignalEvent,
        stats: PipelineStats,
        ctx: ProcessingContext,
    ) -> PipelineResult:
        started_at = ctx.processing_time
        # === IDEMPOTENCY CHECK ===
        if self._repository:
            existing = self._repository.find_by_hash(event.input_event_hash)
            if existing:
                logger.info(
                    "Event %s already processed, returning cached result",
                    event.event_id,
                )
                stats.events_deduplicated = 1
                stats.processing_time_ms = (
                    (datetime.utcnow() - started_at).total_seconds() * 1000
                )
                return PipelineResult(
                    success=True,
                    signals=[existing],
                    stats=stats,
                    cached=True,
                )

        # === LAYER 2: VALIDATION ===
        outcome = self._validator.validate(event, context=ctx)
        if not outcome.passed:
            logger.info(
                "Event %s rejected at validation: %s",
                event.event_id,
                outcome.rejection_reason or "unknown",
            )
            stats.events_rejected_validation = 1
            stats.processing_time_ms = (
                datetime.utcnow() - started_at
            ).total_seconds() * 1000
            return PipelineResult(
                success=True,
                signals=[],
                validation_failures=outcome.results or [],
                stats=stats,
            )
        validated_signal = outcome.signal
        assert validated_signal is not None
        stats.events_validated = 1

        # === LAYER 3: IMPACT TRANSLATION ===
        assessments: list[ImpactAssessment] = []
        for domain in self._config.target_domains:
            assessment = self._translator.translate(
                validated_signal,
                domain=domain,
                context=ctx,
            )
            if assessment:
                assessments.append(assessment)
                logger.info(
                    "Generated assessment for %s: severity=%.2f",
                    domain.value,
                    assessment.overall_severity,
                )

        if not assessments:
            logger.info("Event %s produced no impact assessments", event.event_id)
            stats.events_no_impact = 1
            stats.processing_time_ms = (
                (datetime.utcnow() - started_at).total_seconds() * 1000
            )
            return PipelineResult(success=True, signals=[], stats=stats)

        stats.assessments_generated = len(assessments)

        # === LAYER 4: OUTPUT GENERATION ===
        signals: list[OmenSignal] = []
        for assessment in assessments:
            signal = OmenSignal.from_impact_assessment(
                assessment,
                ruleset_version=ctx.ruleset_version,
                generated_at=ctx.processing_time,
            )
            if signal.confidence_score < self._config.min_confidence_for_output:
                logger.info(
                    "Signal %s below confidence threshold (%.2f < %s)",
                    signal.signal_id,
                    signal.confidence_score,
                    self._config.min_confidence_for_output,
                )
                continue
            signals.append(signal)
            logger.info(
                "Generated OMEN signal: %s [%s] severity=%.2f",
                signal.signal_id,
                signal.confidence_level.value,
                signal.severity,
            )

        stats.signals_generated = len(signals)

        # === PERSIST & PUBLISH (with error handling) ===
        if not self._config.enable_dry_run:
            for signal in signals:
                if self._repository:
                    try:
                        self._repository.save(signal)
                    except PersistenceError as e:
                        logger.error("Failed to persist signal: %s", e)
                    except Exception as e:
                        logger.error(
                            "Unexpected error persisting signal %s: %s",
                            signal.signal_id,
                            e,
                            exc_info=True,
                        )
                if self._publisher:
                    try:
                        self._publisher.publish(signal)
                    except PublishError as e:
                        logger.error(
                            "Failed to publish signal %s: %s",
                            signal.signal_id,
                            e,
                        )
                        if self._config.fail_on_publish_error:
                            raise
                    except Exception as e:
                        logger.error(
                            "Unexpected error publishing signal %s: %s",
                            signal.signal_id,
                            e,
                            exc_info=True,
                        )
                        if self._config.fail_on_publish_error:
                            raise

        stats.processing_time_ms = (
            (datetime.utcnow() - started_at).total_seconds() * 1000
        )
        return PipelineResult(success=True, signals=signals, stats=stats)

    def _handle_omen_error(
        self,
        event: RawSignalEvent,
        error: OmenError,
        stats: PipelineStats,
        ctx: ProcessingContext,
    ) -> PipelineResult:
        """Handle known OMEN errors."""
        logger.error(
            "Pipeline error for %s: %s",
            event.event_id,
            error.message,
            extra={"error": error.to_dict()},
        )
        if self._config.enable_dlq:
            self._dlq.add(event, error)
        stats.events_failed = 1
        stats.processing_time_ms = (
            (datetime.utcnow() - ctx.processing_time).total_seconds() * 1000
        )
        return PipelineResult(
            success=False,
            error=error.message,
            stats=stats,
        )

    def _handle_unexpected_error(
        self,
        event: RawSignalEvent,
        error: Exception,
        stats: PipelineStats,
        ctx: ProcessingContext,
    ) -> PipelineResult:
        """Handle unexpected errors."""
        logger.exception("Unexpected error processing %s", event.event_id)
        omen_error = OmenError(
            f"Unexpected error: {str(error)}",
            context={"exception_type": type(error).__name__},
        )
        if self._config.enable_dlq:
            self._dlq.add(event, omen_error)
        stats.events_failed = 1
        stats.processing_time_ms = (
            (datetime.utcnow() - ctx.processing_time).total_seconds() * 1000
        )
        return PipelineResult(
            success=False,
            error=str(error),
            stats=stats,
        )

    def reprocess_dlq(self, max_items: int = 100) -> list[PipelineResult]:
        """Reprocess items from the dead letter queue."""
        results: list[PipelineResult] = []
        processed = 0
        while processed < max_items:
            entry = self._dlq.pop()
            if entry is None:
                break
            logger.info("Reprocessing DLQ entry: %s", entry.event.event_id)
            result = self.process_single(entry.event)
            results.append(result)
            processed += 1
        return results

    def process_batch(
        self,
        events: Sequence[RawSignalEvent],
    ) -> list[PipelineResult]:
        """Process multiple events. Each event is processed independently."""
        results = []
        for event in events:
            try:
                result = self.process_single(event)
                results.append(result)
            except Exception as e:
                logger.error("Failed to process event %s: %s", event.event_id, e)
                results.append(
                    PipelineResult(
                        success=False,
                        error=str(e),
                        stats=PipelineStats(events_received=1, events_failed=1),
                    )
                )
        return results
