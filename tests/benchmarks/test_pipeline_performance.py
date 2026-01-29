"""Performance benchmarks for OMEN pipeline.

Run with: pytest tests/benchmarks/ -v
Run benchmarks with timings (no coverage failure):
  pytest tests/benchmarks/ -c pytest_benchmark.ini --benchmark-only
  or: pytest tests/benchmarks/ --benchmark-only --no-cov
"""

import asyncio
import concurrent.futures

import pytest

from omen.adapters.inbound.stub_source import StubSignalSource
from omen.adapters.persistence.async_in_memory_repository import (
    AsyncInMemorySignalRepository,
)
from omen.adapters.persistence.in_memory_repository import InMemorySignalRepository
from omen.application.async_pipeline import AsyncOmenPipeline
from omen.application.pipeline import OmenPipeline, PipelineConfig
from omen.domain.rules.validation.liquidity_rule import LiquidityValidationRule
from omen.domain.services.signal_enricher import SignalEnricher
from omen.domain.services.signal_validator import SignalValidator


@pytest.fixture
def sync_pipeline() -> OmenPipeline:
    """Create sync pipeline for benchmarking."""
    return OmenPipeline(
        validator=SignalValidator(rules=[LiquidityValidationRule(min_liquidity_usd=1000.0)]),
        enricher=SignalEnricher(),
        repository=InMemorySignalRepository(),
        publisher=None,
        config=PipelineConfig.default(),
    )


@pytest.fixture
def async_pipeline() -> AsyncOmenPipeline:
    """Create async pipeline for benchmarking."""
    return AsyncOmenPipeline(
        validator=SignalValidator(rules=[LiquidityValidationRule(min_liquidity_usd=1000.0)]),
        enricher=SignalEnricher(),
        repository=AsyncInMemorySignalRepository(),
        publisher=None,
        config=PipelineConfig.default(),
        max_concurrent=10,
    )


class TestSyncPipelinePerformance:
    """Benchmarks for synchronous pipeline."""

    def test_single_event_latency(
        self, sync_pipeline: OmenPipeline, benchmark
    ) -> None:
        """
        Benchmark single event processing latency.

        Target: p99 < 100ms.
        """
        event = StubSignalSource.create_red_sea_event()
        result = benchmark(sync_pipeline.process_single, event)
        assert result.success

    def test_batch_throughput(
        self, sync_pipeline: OmenPipeline, benchmark
    ) -> None:
        """
        Measure batch processing throughput.

        Target: >100 events/second.
        """
        events = [
            StubSignalSource.create_red_sea_event(probability=0.5 + i * 0.004)
            for i in range(100)
        ]
        results = benchmark(sync_pipeline.process_batch, events)
        assert all(r.success for r in results)


class TestAsyncPipelinePerformance:
    """Benchmarks for async pipeline."""

    @pytest.mark.asyncio
    async def test_single_event_latency(
        self, async_pipeline: AsyncOmenPipeline, benchmark
    ) -> None:
        """
        Benchmark async single event latency.

        Target: p99 < 100ms. Runs in a thread to avoid nesting asyncio.run().
        """
        event = StubSignalSource.create_red_sea_event()

        def run():
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
                return ex.submit(
                    asyncio.run, async_pipeline.process_single(event)
                ).result()

        result = benchmark(run)
        assert result.success

    @pytest.mark.asyncio
    async def test_concurrent_throughput(
        self, async_pipeline: AsyncOmenPipeline, benchmark
    ) -> None:
        """
        Measure concurrent processing throughput.

        Target: >200 events/second with concurrency.
        """
        events = [
            StubSignalSource.create_red_sea_event(probability=0.5 + (i % 500) * 0.0008)
            for i in range(500)
        ]

        def run():
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
                return ex.submit(
                    asyncio.run, async_pipeline.process_batch(events)
                ).result()

        results = benchmark(run)
        assert all(r.success for r in results)

    @pytest.mark.asyncio
    async def test_backpressure_handling(
        self, async_pipeline: AsyncOmenPipeline, benchmark
    ) -> None:
        """
        Verify backpressure does not cause failures under load.
        """
        events = [
            StubSignalSource.create_red_sea_event(probability=0.5 + i * 0.0001)
            for i in range(100)
        ]

        def run():
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
                return ex.submit(
                    asyncio.run, async_pipeline.process_batch(events)
                ).result()

        results = benchmark(run)
        assert sum(1 for r in results if r.success) == len(events)


class TestMemoryEfficiency:
    """Memory usage benchmarks."""

    def test_large_batch_memory(
        self, sync_pipeline: OmenPipeline, benchmark
    ) -> None:
        """
        Ensure memory usage is bounded for large batches.
        """
        import tracemalloc

        events = [
            StubSignalSource.create_red_sea_event(probability=0.5 + i * 0.0001)
            for i in range(1000)
        ]

        def run() -> tuple[list, int]:
            tracemalloc.start()
            try:
                results = sync_pipeline.process_batch(events)
                _, peak = tracemalloc.get_traced_memory()
                return results, peak
            finally:
                tracemalloc.stop()

        results, peak = benchmark(run)
        assert all(r.success for r in results)
        peak_mb = peak / 1024 / 1024
        assert peak_mb < 500, f"Peak memory {peak_mb:.1f}MB exceeds 500MB limit"
