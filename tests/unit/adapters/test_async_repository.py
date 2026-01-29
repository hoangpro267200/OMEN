"""
Test async repository CRUD operations.

Coverage target: 80%
Focus: Basic operations, eviction when full
"""

from datetime import datetime

import pytest

from omen.adapters.persistence.async_in_memory_repository import (
    AsyncInMemorySignalRepository,
)
from omen.domain.models.common import (
    EventId,
    ImpactDomain,
    RulesetVersion,
    SignalCategory,
    GeoLocation,
    MarketId,
)
from omen.domain.models.raw_signal import RawSignalEvent, MarketMetadata
from omen.domain.models.omen_signal import OmenSignal
from omen.domain.services.signal_validator import SignalValidator
from omen.domain.services.signal_enricher import SignalEnricher
from omen.domain.rules.validation.liquidity_rule import LiquidityValidationRule
from omen.application.pipeline import OmenPipeline, PipelineConfig
from omen.adapters.persistence.in_memory_repository import InMemorySignalRepository


def _make_sample_signal() -> OmenSignal:
    """Build one OmenSignal via sync pipeline for use in async repo tests."""
    repo = InMemorySignalRepository()
    pipeline = OmenPipeline(
        validator=SignalValidator(
            rules=[LiquidityValidationRule(min_liquidity_usd=100.0)]
        ),
        enricher=SignalEnricher(),
        repository=repo,
        publisher=None,
        config=PipelineConfig.default(),
    )
    event = RawSignalEvent(
        event_id=EventId("async-repo-test-001"),
        title="Red Sea shipping disruption",
        description="Houthi attacks on shipping",
        probability=0.72,
        keywords=["red sea", "shipping", "suez"],
        inferred_locations=[
            GeoLocation(latitude=15.5, longitude=42.5, name="Red Sea", region_code="YE")
        ],
        market=MarketMetadata(
            source="test",
            market_id=MarketId("m1"),
            total_volume_usd=100_000.0,
            current_liquidity_usd=50_000.0,
        ),
    )
    result = pipeline.process_single(event)
    assert result.success and result.signals
    return result.signals[0]


@pytest.fixture
def async_repo() -> AsyncInMemorySignalRepository:
    """Fresh async in-memory repository."""
    return AsyncInMemorySignalRepository()


@pytest.fixture
def small_async_repo() -> AsyncInMemorySignalRepository:
    """Repository with max_size=2 for eviction tests."""
    return AsyncInMemorySignalRepository(max_size=2)


@pytest.fixture
def sample_signal() -> OmenSignal:
    """Single OmenSignal for save/find tests."""
    return _make_sample_signal()


@pytest.fixture
def sample_signals(sample_signal: OmenSignal) -> list[OmenSignal]:
    """Three signals with distinct IDs and hashes for eviction test."""
    s1 = sample_signal
    s2 = sample_signal.model_copy(
        update={"signal_id": "OMEN-EVICT-SIG-002", "input_event_hash": "evict-hash-002"}
    )
    s3 = sample_signal.model_copy(
        update={"signal_id": "OMEN-EVICT-SIG-003", "input_event_hash": "evict-hash-003"}
    )
    return [s1, s2, s3]


@pytest.fixture
def async_repo_with_data(async_repo: AsyncInMemorySignalRepository, sample_signal: OmenSignal):
    """Repository pre-loaded with one signal. Sync fixture that runs async setup."""
    import asyncio
    async def _setup():
        await async_repo.save_async(sample_signal)
        return async_repo
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(_setup())
    finally:
        loop.close()


class TestSaveAsync:
    """Save operation."""

    @pytest.mark.asyncio
    async def test_save_stores_signal(
        self, async_repo: AsyncInMemorySignalRepository, sample_signal: OmenSignal
    ) -> None:
        """Saved signal retrievable by ID."""
        await async_repo.save_async(sample_signal)
        found = await async_repo.find_by_id_async(sample_signal.signal_id)
        assert found is not None
        assert found.signal_id == sample_signal.signal_id
        assert found.source_event_id == sample_signal.source_event_id

    @pytest.mark.asyncio
    async def test_save_indexes_by_hash(
        self, async_repo: AsyncInMemorySignalRepository, sample_signal: OmenSignal
    ) -> None:
        """Saved signal retrievable by hash."""
        await async_repo.save_async(sample_signal)
        found = await async_repo.find_by_hash_async(sample_signal.input_event_hash)
        assert found is not None
        assert found.signal_id == sample_signal.signal_id

    @pytest.mark.asyncio
    async def test_evicts_oldest_when_full(
        self,
        small_async_repo: AsyncInMemorySignalRepository,
        sample_signals: list[OmenSignal],
    ) -> None:
        """At max_size, oldest evicted on new save."""
        s1, s2, s3 = sample_signals
        await small_async_repo.save_async(s1)
        await small_async_repo.save_async(s2)
        assert await small_async_repo.find_by_id_async(s1.signal_id) is not None
        await small_async_repo.save_async(s3)
        assert await small_async_repo.find_by_id_async(s1.signal_id) is None
        assert await small_async_repo.find_by_hash_async(s1.input_event_hash) is None
        assert await small_async_repo.find_by_id_async(s2.signal_id) is not None
        assert await small_async_repo.find_by_id_async(s3.signal_id) is not None


class TestFindAsync:
    """Find operations."""

    @pytest.mark.asyncio
    async def test_find_by_id_returns_signal(
        self,
        async_repo_with_data: AsyncInMemorySignalRepository,
        sample_signal: OmenSignal,
    ) -> None:
        """Existing ID → signal returned."""
        found = await async_repo_with_data.find_by_id_async(sample_signal.signal_id)
        assert found is not None
        assert found.signal_id == sample_signal.signal_id

    @pytest.mark.asyncio
    async def test_find_by_id_returns_none_missing(
        self, async_repo: AsyncInMemorySignalRepository
    ) -> None:
        """Missing ID → None."""
        found = await async_repo.find_by_id_async("nonexistent-id")
        assert found is None

    @pytest.mark.asyncio
    async def test_find_by_hash_returns_signal(
        self,
        async_repo_with_data: AsyncInMemorySignalRepository,
        sample_signal: OmenSignal,
    ) -> None:
        """Existing hash → signal returned."""
        found = await async_repo_with_data.find_by_hash_async(
            sample_signal.input_event_hash
        )
        assert found is not None
        assert found.signal_id == sample_signal.signal_id

    @pytest.mark.asyncio
    async def test_find_by_hash_returns_none_missing(
        self, async_repo: AsyncInMemorySignalRepository
    ) -> None:
        """Missing hash → None."""
        found = await async_repo.find_by_hash_async("nonexistent-hash")
        assert found is None

    @pytest.mark.asyncio
    async def test_find_recent_returns_newest_first(
        self,
        async_repo: AsyncInMemorySignalRepository,
        sample_signal: OmenSignal,
    ) -> None:
        """Results ordered by insertion (newest first in reversed store)."""
        s2 = sample_signal.model_copy(update={"signal_id": "OMEN-RECENT-002"})
        await async_repo.save_async(sample_signal)
        await async_repo.save_async(s2)
        recent = await async_repo.find_recent_async(limit=10)
        assert len(recent) == 2
        assert recent[0].signal_id == s2.signal_id
        assert recent[1].signal_id == sample_signal.signal_id

    @pytest.mark.asyncio
    async def test_find_recent_respects_limit(
        self,
        async_repo: AsyncInMemorySignalRepository,
        sample_signals: list[OmenSignal],
    ) -> None:
        """limit=3 → max 3 results."""
        for s in sample_signals:
            await async_repo.save_async(s)
        recent = await async_repo.find_recent_async(limit=2)
        assert len(recent) == 2

    @pytest.mark.asyncio
    async def test_find_recent_filters_by_since(
        self,
        async_repo: AsyncInMemorySignalRepository,
        sample_signal: OmenSignal,
    ) -> None:
        """since filter excludes older signals."""
        from datetime import timedelta

        await async_repo.save_async(sample_signal)
        since = sample_signal.generated_at + timedelta(seconds=1)
        recent = await async_repo.find_recent_async(limit=10, since=since)
        assert len(recent) == 0
        since_old = sample_signal.generated_at - timedelta(seconds=1)
        recent2 = await async_repo.find_recent_async(limit=10, since=since_old)
        assert len(recent2) == 1
