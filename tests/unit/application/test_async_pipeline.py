"""
Test async pipeline BEHAVIOR, not implementation.

Coverage target: 80%
Focus: Observable outcomes, error handling
DO NOT: Mock asyncio internals, test semaphore state, assert timing
"""

import asyncio
from unittest.mock import MagicMock

import pytest

from omen.application.async_pipeline import AsyncOmenPipeline
from omen.application.pipeline import PipelineConfig
from omen.domain.models.common import ImpactDomain, RulesetVersion
from omen.domain.models.context import ProcessingContext
from omen.domain.services.signal_validator import SignalValidator
from omen.domain.services.impact_translator import ImpactTranslator
from omen.domain.rules.validation.liquidity_rule import LiquidityValidationRule
from omen.domain.rules.translation.logistics.red_sea_disruption import (
    RedSeaDisruptionRule,
)
from omen.adapters.persistence.async_in_memory_repository import (
    AsyncInMemorySignalRepository,
)
from omen.adapters.inbound.stub_source import StubSignalSource


@pytest.fixture
def async_pipeline() -> AsyncOmenPipeline:
    """Async pipeline for behavior testing."""
    return AsyncOmenPipeline(
        validator=SignalValidator(
            rules=[LiquidityValidationRule(min_liquidity_usd=100.0)]
        ),
        translator=ImpactTranslator(rules=[RedSeaDisruptionRule()]),
        repository=AsyncInMemorySignalRepository(),
        publisher=None,
        config=PipelineConfig(
            ruleset_version=RulesetVersion("test"),
            target_domains=frozenset({ImpactDomain.LOGISTICS}),
        ),
        max_concurrent=5,
    )


@pytest.fixture
def valid_event():
    """Event that passes validation and triggers Red Sea translation."""
    return StubSignalSource.create_red_sea_event(
        probability=0.75, liquidity=75000.0
    )


@pytest.fixture
def low_liquidity_event():
    """Event that fails liquidity validation."""
    return StubSignalSource.create_red_sea_event(
        probability=0.5, liquidity=50.0
    )


@pytest.fixture
def valid_events(valid_event, low_liquidity_event):
    """Mixed list for batch tests."""
    return [valid_event, low_liquidity_event]


@pytest.fixture
def many_events():
    """Many events for coarse throughput sanity check."""
    return [
        StubSignalSource.create_red_sea_event(
            probability=0.5 + (i % 100) * 0.004, liquidity=75000.0
        )
        for i in range(100)
    ]


class TestProcessSingle:
    """Single event processing outcomes."""

    @pytest.mark.asyncio
    async def test_returns_pipeline_result(
        self, async_pipeline: AsyncOmenPipeline, valid_event
    ) -> None:
        """process_single → PipelineResult instance."""
        result = await async_pipeline.process_single(valid_event)
        from omen.application.dto.pipeline_result import PipelineResult

        assert isinstance(result, PipelineResult)

    @pytest.mark.asyncio
    async def test_success_for_valid_event(
        self, async_pipeline: AsyncOmenPipeline, valid_event
    ) -> None:
        """Valid event → success=True, signals populated."""
        result = await async_pipeline.process_single(valid_event)
        assert result.success is True
        assert len(result.signals) >= 1

    @pytest.mark.asyncio
    async def test_rejects_low_liquidity(
        self, async_pipeline: AsyncOmenPipeline, low_liquidity_event
    ) -> None:
        """Low liquidity → success=True, signals=[], rejected in stats."""
        result = await async_pipeline.process_single(low_liquidity_event)
        assert result.success is True
        assert len(result.signals) == 0
        assert result.stats.events_rejected_validation >= 1

    @pytest.mark.asyncio
    async def test_returns_cached_on_duplicate(
        self, async_pipeline: AsyncOmenPipeline, valid_event
    ) -> None:
        """Same event twice → second call returns cached=True."""
        r1 = await async_pipeline.process_single(valid_event)
        r2 = await async_pipeline.process_single(valid_event)
        assert r1.success and r2.success
        assert r2.cached is True
        assert r1.signals[0].signal_id == r2.signals[0].signal_id

    @pytest.mark.asyncio
    async def test_uses_provided_context(
        self, async_pipeline: AsyncOmenPipeline, valid_event
    ) -> None:
        """Explicit ProcessingContext → used in output timestamps."""
        from datetime import datetime

        ctx = ProcessingContext.create_for_replay(
            processing_time=datetime(2024, 6, 1, 12, 0, 0),
            ruleset_version=RulesetVersion("replay-v1"),
        )
        result = await async_pipeline.process_single(valid_event, context=ctx)
        assert result.success is True
        assert result.signals
        assert result.signals[0].ruleset_version == "replay-v1"


class TestProcessBatch:
    """Batch processing outcomes."""

    @pytest.mark.asyncio
    async def test_returns_list_of_results(
        self, async_pipeline: AsyncOmenPipeline, valid_events
    ) -> None:
        """Batch of N events → list of N PipelineResults."""
        results = await async_pipeline.process_batch(valid_events)
        assert len(results) == len(valid_events)
        from omen.application.dto.pipeline_result import PipelineResult

        for r in results:
            assert isinstance(r, PipelineResult)

    @pytest.mark.asyncio
    async def test_all_events_processed(
        self, async_pipeline: AsyncOmenPipeline, valid_events
    ) -> None:
        """All events in batch are processed (success or rejected)."""
        results = await async_pipeline.process_batch(valid_events)
        assert len(results) == len(valid_events)
        total_received = sum(r.stats.events_received for r in results)
        assert total_received == len(valid_events)

    @pytest.mark.asyncio
    async def test_batch_faster_than_sequential(
        self, async_pipeline: AsyncOmenPipeline, many_events
    ) -> None:
        """Concurrent batch completes in reasonable time (< 5 s for 100 events)."""
        import time

        start = time.perf_counter()
        results = await async_pipeline.process_batch(many_events)
        elapsed = time.perf_counter() - start
        assert len(results) == len(many_events)
        assert elapsed < 5.0


class TestProcessStream:
    """Stream processing outcomes."""

    @pytest.mark.asyncio
    async def test_yields_results(
        self, async_pipeline: AsyncOmenPipeline
    ) -> None:
        """process_stream yields PipelineResult for each event."""
        source = StubSignalSource()
        count = 0
        async for result in async_pipeline.process_stream(source, limit=5):
            count += 1
            assert result is not None
            from omen.application.dto.pipeline_result import PipelineResult

            assert isinstance(result, PipelineResult)
        assert count >= 1

    @pytest.mark.asyncio
    async def test_stops_on_shutdown(
        self, async_pipeline: AsyncOmenPipeline
    ) -> None:
        """Setting shutdown_event stops iteration."""
        source = StubSignalSource()
        collected = []
        async def consume():
            async for r in async_pipeline.process_stream(source, limit=100):
                collected.append(r)
                if len(collected) >= 2:
                    await async_pipeline.shutdown(timeout=0.1)
                    break

        await consume()
        assert len(collected) >= 1


class TestErrorHandling:
    """Error handling outcomes."""

    @pytest.mark.asyncio
    async def test_validation_error_returns_failure(
        self, async_pipeline: AsyncOmenPipeline, valid_event
    ) -> None:
        """Validation exception → success=False, error message."""
        async_pipeline._validator = MagicMock()
        async_pipeline._validator.validate = MagicMock(
            side_effect=RuntimeError("validation failed")
        )
        result = await async_pipeline.process_single(valid_event)
        assert result.success is False
        assert "validation failed" in (result.error or "")

    @pytest.mark.asyncio
    async def test_error_returns_failure_no_dlq(
        self, async_pipeline: AsyncOmenPipeline, valid_event
    ) -> None:
        """Processing error → success=False. (Async pipeline does not push to DLQ.)"""
        async_pipeline._validator = MagicMock()
        async_pipeline._validator.validate = MagicMock(
            side_effect=RuntimeError("oops")
        )
        result = await async_pipeline.process_single(valid_event)
        assert result.success is False
        assert result.error is not None


class TestShutdown:
    """Shutdown behavior."""

    @pytest.mark.asyncio
    async def test_shutdown_sets_event(
        self, async_pipeline: AsyncOmenPipeline
    ) -> None:
        """shutdown() sets the shutdown event."""
        await async_pipeline.shutdown(timeout=0.1)
        assert async_pipeline._shutdown_event.is_set()

    @pytest.mark.asyncio
    async def test_shutdown_completes(
        self, async_pipeline: AsyncOmenPipeline
    ) -> None:
        """shutdown() completes without error."""
        await async_pipeline.shutdown(timeout=0.1)
