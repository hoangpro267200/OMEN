"""
Legacy impact-based pipeline — DEPRECATED.

Use omen.application.pipeline.OmenPipeline for signal-only output.
Impact assessment should be performed by downstream consumers.
This module lives in omen_impact so OMEN core stays impact-free.
"""

from omen.application.dto.pipeline_result import PipelineResult, PipelineStats
from omen.application.pipeline import PipelineConfig
from omen.application.ports.output_publisher import OutputPublisher
from omen.application.ports.signal_repository import SignalRepository
from omen.domain.models.context import ProcessingContext
from omen.domain.models.raw_signal import RawSignalEvent
from omen.domain.services.signal_validator import SignalValidator
from omen.infrastructure.dead_letter import DeadLetterQueue

from omen_impact.assessment import ImpactAssessment
from omen_impact.legacy_signal import LegacyOmenSignal
from omen_impact.translator import ImpactTranslator


class LegacyPipeline:
    """
    DEPRECATED: Impact-based pipeline.

    Use OmenPipeline for signal-only output. Impact assessment
    should be performed by downstream consumers.
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

    def process_single(
        self,
        event: RawSignalEvent,
        context: ProcessingContext | None = None,
    ) -> PipelineResult:
        """Process via validate → impact translate → LegacyOmenSignal."""
        ctx = context or ProcessingContext.create(self._config.ruleset_version)
        stats = PipelineStats()
        stats.events_received = 1
        outcome = self._validator.validate(event, context=ctx)
        if not outcome.passed:
            stats.events_rejected_validation = 1
            return PipelineResult(
                success=True,
                signals=[],
                validation_failures=outcome.results or [],
                stats=stats,
            )
        validated_signal = outcome.signal
        if not validated_signal:
            return PipelineResult(success=True, signals=[], stats=stats)
        stats.events_validated = 1
        assessments: list[ImpactAssessment] = []
        for domain in self._config.target_domains:
            a = self._translator.translate(validated_signal, domain=domain, context=ctx)
            if a:
                assessments.append(a)
        if not assessments:
            stats.events_no_impact = 1
            return PipelineResult(success=True, signals=[], stats=stats)
        legacy_signals: list[LegacyOmenSignal] = []
        for assessment in assessments:
            s = LegacyOmenSignal.from_impact_assessment(
                assessment,
                ruleset_version=ctx.ruleset_version,
                generated_at=ctx.processing_time,
            )
            if s.confidence_score >= self._config.min_confidence_for_output:
                legacy_signals.append(s)
        stats.signals_generated = len(legacy_signals)
        stats.assessments_generated = len(assessments)
        return PipelineResult(success=True, signals=legacy_signals, stats=stats)
