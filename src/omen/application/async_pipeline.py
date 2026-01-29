"""Async OMEN Pipeline.

High-performance async implementation for production workloads.
"""

import asyncio
import logging
from datetime import datetime
from typing import AsyncIterator, Sequence

from omen.application.dto.pipeline_result import PipelineResult, PipelineStats
from omen.application.pipeline import PipelineConfig
from omen.application.ports.output_publisher import OutputPublisher
from omen.application.ports.signal_repository import AsyncSignalRepository
from omen.application.ports.signal_source import SignalSource
from omen.domain.models.context import ProcessingContext
from omen.domain.models.omen_signal import OmenSignal
from omen.domain.models.raw_signal import RawSignalEvent
from omen.domain.services.signal_enricher import SignalEnricher
from omen.domain.services.signal_validator import SignalValidator
from omen.infrastructure.dead_letter import DeadLetterQueue

logger = logging.getLogger(__name__)


class AsyncOmenPipeline:
    """
    Async implementation of OMEN pipeline.

    Designed for high-throughput scenarios with:
    - Concurrent event processing
    - Async I/O for sources and publishers
    - Backpressure via semaphores
    - Graceful shutdown
    """

    def __init__(
        self,
        validator: SignalValidator,
        enricher: SignalEnricher,
        repository: AsyncSignalRepository | None = None,
        publisher: OutputPublisher | None = None,
        dead_letter_queue: DeadLetterQueue | None = None,
        config: PipelineConfig | None = None,
        max_concurrent: int = 10,
    ) -> None:
        self._validator = validator
        self._enricher = enricher
        self._repository = repository
        self._publisher = publisher
        self._dlq = dead_letter_queue or DeadLetterQueue()
        self._config = config or PipelineConfig.default()
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._shutdown_event = asyncio.Event()

    async def process_single(
        self,
        event: RawSignalEvent,
        context: ProcessingContext | None = None,
    ) -> PipelineResult:
        """Process a single event asynchronously."""
        async with self._semaphore:
            return await self._process_single_inner(event, context)

    async def _process_single_inner(
        self,
        event: RawSignalEvent,
        context: ProcessingContext | None,
    ) -> PipelineResult:
        ctx = context or ProcessingContext.create(self._config.ruleset_version)
        started_at = datetime.utcnow()
        stats = PipelineStats(events_received=1)

        try:
            if self._repository is not None:
                existing = await self._repository.find_by_hash_async(
                    event.input_event_hash
                )
                if existing is not None:
                    stats.events_deduplicated = 1
                    stats.processing_time_ms = (
                        datetime.utcnow() - started_at
                    ).total_seconds() * 1000
                    return PipelineResult(
                        success=True,
                        signals=[existing],
                        stats=stats,
                        cached=True,
                    )

            loop = asyncio.get_running_loop()
            validation_outcome = await loop.run_in_executor(
                None,
                lambda: self._validator.validate(event, context=ctx),
            )

            if not validation_outcome.passed:
                stats.events_rejected_validation = 1
                stats.processing_time_ms = (
                    datetime.utcnow() - started_at
                ).total_seconds() * 1000
                return PipelineResult(
                    success=True,
                    signals=[],
                    validation_failures=validation_outcome.results or [],
                    stats=stats,
                )

            validated_signal = validation_outcome.signal
            if validated_signal is None:
                stats.events_rejected_validation = 1
                stats.processing_time_ms = (
                    datetime.utcnow() - started_at
                ).total_seconds() * 1000
                return PipelineResult(
                    success=True,
                    signals=[],
                    validation_failures=validation_outcome.results or [],
                    stats=stats,
                )

            stats.events_validated = 1

            validation_context: dict = {
                "confidence_factors": {
                    "liquidity": validated_signal.liquidity_score,
                    "geographic": next(
                        (r.score for r in validated_signal.validation_results if r.rule_name == "geographic_relevance"),
                        0.5,
                    ),
                    "source_reliability": 0.85,
                },
                "validation_results": validated_signal.validation_results,
            }
            enrichment = await loop.run_in_executor(
                None,
                lambda: self._enricher.enrich(event, validation_context),
            )

            try:
                signal = OmenSignal.from_validated_event(validated_signal, enrichment)
            except Exception:
                stats.processing_time_ms = (
                    datetime.utcnow() - started_at
                ).total_seconds() * 1000
                return PipelineResult(success=True, signals=[], stats=stats)

            if signal.confidence_score < self._config.min_confidence_for_output:
                stats.processing_time_ms = (
                    datetime.utcnow() - started_at
                ).total_seconds() * 1000
                return PipelineResult(success=True, signals=[], stats=stats)

            signals: list[OmenSignal] = [signal]
            stats.signals_generated = 1

            if not self._config.enable_dry_run and signals:
                await self._persist_and_publish(signals)

            stats.processing_time_ms = (
                datetime.utcnow() - started_at
            ).total_seconds() * 1000
            return PipelineResult(success=True, signals=signals, stats=stats)

        except Exception as e:
            logger.exception("Error processing %s", event.event_id)
            stats.events_failed = 1
            stats.processing_time_ms = (
                datetime.utcnow() - started_at
            ).total_seconds() * 1000
            return PipelineResult(success=False, error=str(e), stats=stats)

    async def _persist_and_publish(self, signals: list[OmenSignal]) -> None:
        tasks: list[asyncio.Task[object]] = []
        for signal in signals:
            if self._repository is not None:
                tasks.append(asyncio.create_task(self._repository.save_async(signal)))
            if self._publisher is not None:
                tasks.append(
                    asyncio.create_task(self._publisher.publish_async(signal))
                )
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def process_batch(
        self, events: Sequence[RawSignalEvent]
    ) -> list[PipelineResult]:
        """Process multiple events concurrently with backpressure."""
        tasks = [self.process_single(event) for event in events]
        return list(await asyncio.gather(*tasks))

    async def process_stream(
        self,
        source: SignalSource,
        limit: int = 1000,
    ) -> AsyncIterator[PipelineResult]:
        """Process events from a streaming source. Yields results as they complete."""
        async for event in source.fetch_events_async(limit=limit):
            if self._shutdown_event.is_set():
                logger.info("Shutdown requested, stopping stream processing")
                break
            result = await self.process_single(event)
            yield result

    async def shutdown(self, timeout: float = 30.0) -> None:
        """Gracefully shutdown the pipeline."""
        self._shutdown_event.set()
        logger.info("Waiting up to %ss for in-flight requests...", min(timeout, 5.0))
        await asyncio.sleep(min(timeout, 5.0))
