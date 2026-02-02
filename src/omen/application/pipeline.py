"""OMEN Main Pipeline.

Default path: Layer 1 (Signal Sourcing) → Layer 2 (Validation) →
Layer 3 (Enrichment) → Layer 4 (Pure OmenSignal output).

No impact translation in the default path. Impact assessment belongs
in downstream consumers (e.g. RiskCast).

Impact assessment is performed by downstream consumers (e.g. RiskCast).
Legacy path: use omen_impact.LegacyPipeline and omen_impact.LegacyOmenSignal.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Sequence
import logging

from ..domain.models.common import RulesetVersion, ImpactDomain
from ..domain.models.context import ProcessingContext
from ..domain.models.raw_signal import RawSignalEvent
from ..domain.models.validated_signal import ValidatedSignal
from ..domain.models.omen_signal import OmenSignal

from ..domain.services.signal_validator import SignalValidator, ValidationOutcome
from ..domain.services.signal_enricher import SignalEnricher
from ..domain.errors import OmenError, PersistenceError, PublishError

from ..infrastructure.dead_letter import DeadLetterQueue
from ..infrastructure.storage.signal_history import get_signal_history_store
from ..infrastructure.metrics.pipeline_metrics import get_metrics_collector
from ..infrastructure.activity.activity_logger import get_activity_logger
from ..infrastructure.realtime.price_streamer import get_price_streamer
from ..infrastructure.debug.rejection_tracker import get_rejection_tracker

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
    The main OMEN intelligence pipeline (signal-only).

    Stages: Validate → Enrich → OmenSignal (pure contract).
    Produces structured signals with probability, confidence, and context.
    No impact calculations — those belong in downstream consumers.
    """

    def __init__(
        self,
        validator: SignalValidator,
        enricher: SignalEnricher,
        repository: SignalRepository | None = None,
        publisher: OutputPublisher | None = None,
        dead_letter_queue: DeadLetterQueue | None = None,
        config: PipelineConfig | None = None,
    ):
        self._validator = validator
        self._enricher = enricher
        self._repository = repository
        self._publisher = publisher
        self._dlq = dead_letter_queue if dead_letter_queue is not None else DeadLetterQueue()
        self._config = config or PipelineConfig.default()

        logger.info(
            "Pipeline initialized (signal-only) with ruleset %s",
            self._config.ruleset_version,
        )

    def _record_metrics(self, result: PipelineResult) -> None:
        """Record pipeline result into the metrics collector (real stats)."""
        try:
            s = result.stats
            get_metrics_collector().record_from_pipeline_result(
                events_received=s.events_received,
                events_validated=s.events_validated,
                events_rejected=s.events_rejected_validation,
                signals_generated=s.signals_generated,
                processing_time_ms=s.processing_time_ms,
                signals=result.signals,
            )
        except Exception as e:
            logger.warning("Failed to record pipeline metrics: %s", e)

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
                    datetime.now(timezone.utc) - started_at
                ).total_seconds() * 1000
                result = PipelineResult(
                    success=True,
                    signals=[existing],
                    stats=stats,
                    cached=True,
                )
                self._record_metrics(result)
                return result

        # === LAYER 2: VALIDATION ===
        outcome = self._validator.validate(event, context=ctx)
        if not outcome.passed:
            try:
                tracker = get_rejection_tracker()
                first_result = outcome.results[0] if outcome.results else None
                tracker.record_rejection(
                    event_id=str(event.event_id),
                    stage="validation",
                    reason=outcome.rejection_reason or "unknown",
                    title=event.title,
                    probability=event.probability,
                    liquidity=event.market.current_liquidity_usd,
                    keywords_found=list(event.keywords) if event.keywords else [],
                    rule_name=first_result.rule_name if first_result else None,
                    rule_version=first_result.rule_version if first_result else None,
                )
            except Exception as e:
                logger.warning("Failed to record validation rejection: %s", e)
            logger.info(
                "Event %s rejected at validation: %s",
                event.event_id,
                outcome.rejection_reason or "unknown",
            )
            stats.events_rejected_validation = 1
            stats.processing_time_ms = (
                datetime.now(timezone.utc) - started_at
            ).total_seconds() * 1000
            result = PipelineResult(
                success=True,
                signals=[],
                validation_failures=outcome.results or [],
                stats=stats,
            )
            try:
                activity = get_activity_logger()
                rule_name = outcome.results[0].rule_name if outcome.results else "validation"
                activity.log_event_validated(
                    event_id=str(event.event_id),
                    market_id=str(event.market.market_id),
                    rule_name=rule_name,
                    passed=False,
                    reason=outcome.rejection_reason,
                )
            except Exception as e:
                logger.warning("Failed to log validation activity: %s", e)
            self._record_metrics(result)
            return result
        validated_signal = outcome.signal
        assert validated_signal is not None
        stats.events_validated = 1
        try:
            activity = get_activity_logger()
            rule_name = outcome.results[-1].rule_name if outcome.results else "validation"
            activity.log_event_validated(
                event_id=str(event.event_id),
                market_id=str(event.market.market_id),
                rule_name=rule_name,
                passed=True,
            )
        except Exception as e:
            logger.warning("Failed to log validation activity: %s", e)

        # === LAYER 3: ENRICHMENT (no impact translation) ===
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
        enrichment = self._enricher.enrich(event, validation_context)

        # === LAYER 4: PURE OMEN SIGNAL ===
        try:
            signal = OmenSignal.from_validated_event(validated_signal, enrichment)
        except Exception as e:
            logger.warning("Failed to build OmenSignal: %s", e)
            try:
                get_rejection_tracker().record_rejection(
                    event_id=str(event.event_id),
                    stage="generation",
                    reason=str(e),
                    title=event.title,
                    probability=event.probability,
                )
            except Exception as e2:
                logger.warning("Failed to record generation rejection: %s", e2)
            stats.processing_time_ms = (
                datetime.now(timezone.utc) - started_at
            ).total_seconds() * 1000
            result = PipelineResult(success=True, signals=[], stats=stats)
            self._record_metrics(result)
            return result

        if signal.confidence_score < self._config.min_confidence_for_output:
            try:
                get_rejection_tracker().record_rejection(
                    event_id=str(event.event_id),
                    stage="generation",
                    reason=f"Below confidence threshold ({signal.confidence_score:.2f} < {self._config.min_confidence_for_output})",
                    title=event.title,
                    probability=event.probability,
                    details={"confidence_score": signal.confidence_score},
                )
            except Exception as e:
                logger.warning("Failed to record generation rejection: %s", e)
            logger.info(
                "Signal %s below confidence threshold (%.2f < %s)",
                signal.signal_id,
                signal.confidence_score,
                self._config.min_confidence_for_output,
            )
            stats.processing_time_ms = (
                datetime.now(timezone.utc) - started_at
            ).total_seconds() * 1000
            result = PipelineResult(success=True, signals=[], stats=stats)
            self._record_metrics(result)
            return result

        try:
            get_rejection_tracker().record_passed(
                signal_id=signal.signal_id,
                event_id=str(event.event_id),
                title=signal.title,
                probability=signal.probability,
                confidence=signal.confidence_score,
                confidence_level=signal.confidence_level.value,
                metrics_count=0,
                routes_count=0,
            )
        except Exception as e:
            logger.warning("Failed to record passed signal: %s", e)

        signals: list[OmenSignal] = [signal]
        stats.signals_generated = 1

        try:
            get_signal_history_store().record(
                signal_id=signal.signal_id,
                probability=signal.probability,
                source="polymarket_gamma",
                market_id=str(event.market.market_id),
            )
        except Exception as e:
            logger.warning("Failed to record signal history: %s", e)

        token_id = getattr(event.market, "condition_token_id", None) or (
            (event.market.clob_token_ids or [None])[0]
            if getattr(event.market, "clob_token_ids", None)
            else None
        )
        if token_id:
            try:
                get_price_streamer().register_signal(
                    signal_id=signal.signal_id,
                    token_id=token_id,
                    initial_price=signal.probability,
                )
            except Exception as e:
                logger.warning("Failed to register signal for real-time: %s", e)

        try:
            get_activity_logger().log_signal_generated(
                signal_id=signal.signal_id,
                title=signal.title,
                confidence_label=signal.confidence_level.value,
                confidence_level=signal.confidence_level.value,
            )
        except Exception as e:
            logger.warning("Failed to log signal activity: %s", e)

        logger.info(
            "Generated OMEN signal: %s [%s]",
            signal.signal_id,
            signal.confidence_level.value,
        )

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

        stats.processing_time_ms = (datetime.now(timezone.utc) - started_at).total_seconds() * 1000
        result = PipelineResult(success=True, signals=signals, stats=stats)
        self._record_metrics(result)
        return result

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
            datetime.now(timezone.utc) - ctx.processing_time
        ).total_seconds() * 1000
        result = PipelineResult(
            success=False,
            error=error.message,
            stats=stats,
        )
        self._record_metrics(result)
        return result

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
            datetime.now(timezone.utc) - ctx.processing_time
        ).total_seconds() * 1000
        result = PipelineResult(
            success=False,
            error=str(error),
            stats=stats,
        )
        self._record_metrics(result)
        return result

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
