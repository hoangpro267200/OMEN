"""Pytest configuration and shared fixtures.

All fixtures use current domain models:
- RawSignalEvent (event_id, title, probability, market=MarketMetadata)
- ValidatedSignal, ValidationResult, ExplanationChain, ExplanationStep
- Enums: SignalCategory, ValidationStatus, ImpactDomain, ConfidenceLevel, RulesetVersion
"""

from datetime import datetime
from unittest.mock import MagicMock

import pytest

from omen.domain.models.common import (
    EventId,
    ImpactDomain,
    MarketId,
    RulesetVersion,
    GeoLocation,
    ProbabilityMovement,
    SignalCategory,
    ValidationStatus,
    generate_deterministic_hash,
)
from omen.domain.models.raw_signal import RawSignalEvent, MarketMetadata
from omen.domain.models.validated_signal import ValidatedSignal, ValidationResult
from omen.domain.models.context import ProcessingContext
from omen.domain.models.explanation import ExplanationChain, ExplanationStep
from omen.adapters.inbound.stub_source import StubSignalSource
from omen.adapters.persistence.in_memory_repository import InMemorySignalRepository
from omen.adapters.persistence.async_in_memory_repository import (
    AsyncInMemorySignalRepository,
)
from omen.application.pipeline import OmenPipeline, PipelineConfig
from omen.application.async_pipeline import AsyncOmenPipeline
from omen.domain.services.signal_validator import SignalValidator
from omen.domain.services.signal_enricher import SignalEnricher
from omen.domain.rules.validation.liquidity_rule import LiquidityValidationRule
from omen.adapters.outbound.console_publisher import ConsolePublisher
from omen.infrastructure.dead_letter import DeadLetterQueue


@pytest.fixture
def ruleset_version() -> RulesetVersion:
    """Standard ruleset version for tests."""
    return RulesetVersion("test-v1.0.0")


@pytest.fixture
def processing_context(ruleset_version: RulesetVersion) -> ProcessingContext:
    """Fixed-time processing context for deterministic tests."""
    return ProcessingContext.create_for_replay(
        processing_time=datetime(2025, 1, 15, 12, 0, 0),
        ruleset_version=ruleset_version,
    )


@pytest.fixture
def high_quality_event() -> RawSignalEvent:
    """A high-quality event that should pass all validation (liquidity + Red Sea translation)."""
    return RawSignalEvent(
        event_id=EventId("test-hq-001"),
        title="Red Sea shipping disruption due to Houthi attacks",
        description="Significant commercial shipping disruption expected",
        probability=0.75,
        movement=ProbabilityMovement(
            current=0.75,
            previous=0.60,
            delta=0.15,
            window_hours=24,
        ),
        keywords=["red sea", "shipping", "houthi", "suez"],
        inferred_locations=[
            GeoLocation(
                latitude=15.5, longitude=42.5, name="Red Sea", region_code="YE"
            )
        ],
        market=MarketMetadata(
            source="test",
            market_id=MarketId("test-001"),
            total_volume_usd=500000.0,
            current_liquidity_usd=75000.0,
            num_traders=1200,
        ),
    )


@pytest.fixture
def low_liquidity_event() -> RawSignalEvent:
    """An event with insufficient liquidity (fails liquidity check)."""
    return RawSignalEvent(
        event_id=EventId("test-low-liq-001"),
        title="Minor shipping delay",
        probability=0.50,
        keywords=["shipping", "delay"],
        market=MarketMetadata(
            source="test",
            market_id=MarketId("test-002"),
            total_volume_usd=500.0,
            current_liquidity_usd=50.0,
        ),
    )


@pytest.fixture
def red_sea_event() -> RawSignalEvent:
    """Event that triggers Red Sea disruption translation (high liquidity + Red Sea keywords)."""
    return RawSignalEvent(
        event_id=EventId("test-red-sea-001"),
        title="Red Sea shipping disruption due to Houthi attacks",
        description="Will commercial shipping through the Red Sea be significantly disrupted?",
        probability=0.75,
        movement=ProbabilityMovement(
            current=0.75, previous=0.60, delta=0.15, window_hours=24
        ),
        keywords=["red sea", "shipping", "houthi", "yemen", "suez"],
        inferred_locations=[
            GeoLocation(
                latitude=15.5, longitude=42.5, name="Red Sea", region_code="YE"
            )
        ],
        market=MarketMetadata(
            source="stub",
            market_id=MarketId("stub-market-001"),
            market_url="https://example.com/market/001",
            total_volume_usd=500000.0,
            current_liquidity_usd=75000.0,
            num_traders=1200,
        ),
    )


@pytest.fixture
def irrelevant_event() -> RawSignalEvent:
    """Event with no logistics/Red Sea relevance — should produce no impact (after liquidity pass)."""
    return RawSignalEvent(
        event_id=EventId("test-irrelevant-001"),
        title="Will it rain in Tokyo next week?",
        description="Weather prediction market.",
        probability=0.3,
        keywords=["weather", "rain", "tokyo"],
        market=MarketMetadata(
            source="test",
            market_id=MarketId("test-003"),
            total_volume_usd=10000.0,
            current_liquidity_usd=5000.0,
        ),
    )


def _make_validation_result_passed(score: float = 0.9) -> ValidationResult:
    return ValidationResult(
        rule_name="liquidity_validation",
        rule_version="1.0.0",
        status=ValidationStatus.PASSED,
        score=score,
        reason=f"Sufficient liquidity (score={score})",
    )


@pytest.fixture
def validated_red_sea_signal(
    high_quality_event: RawSignalEvent,
    ruleset_version: RulesetVersion,
    processing_context: ProcessingContext,
) -> ValidatedSignal:
    """A validated signal about Red Sea disruption (as if it passed validation)."""
    step = ExplanationStep.create(
        step_id=1,
        rule_name="liquidity_validation",
        rule_version="1.0.0",
        reasoning="Sufficient liquidity",
        confidence_contribution=0.27,
        processing_time=processing_context.processing_time,
        input_summary={"current_liquidity_usd": 75000.0},
        output_summary={"status": "PASSED", "score": 0.9},
    )
    chain = (
        ExplanationChain.create(processing_context)
        .add_step(step)
        .finalize(processing_context)
    )
    return ValidatedSignal(
        event_id=high_quality_event.event_id,
        original_event=high_quality_event,
        category=SignalCategory.GEOPOLITICAL,
        relevant_locations=high_quality_event.inferred_locations,
        affected_chokepoints=["Red Sea", "Suez Canal"],
        validation_results=[_make_validation_result_passed(0.9)],
        overall_validation_score=0.9,
        signal_strength=0.9,
        liquidity_score=0.9,
        explanation=chain,
        ruleset_version=ruleset_version,
        validated_at=processing_context.processing_time,
    )


@pytest.fixture
def stub_source() -> StubSignalSource:
    """Pre-configured stub source with default events."""
    return StubSignalSource()


@pytest.fixture
def in_memory_repository() -> InMemorySignalRepository:
    """Fresh in-memory repository for each test."""
    return InMemorySignalRepository()


@pytest.fixture
def pipeline(
    in_memory_repository: InMemorySignalRepository,
) -> OmenPipeline:
    """OmenPipeline with LiquidityValidationRule, enricher, stub repo and console publisher."""
    validator = SignalValidator(rules=[LiquidityValidationRule(min_liquidity_usd=1000.0)])
    enricher = SignalEnricher()
    publisher = ConsolePublisher()
    return OmenPipeline(
        validator=validator,
        enricher=enricher,
        repository=in_memory_repository,
        publisher=publisher,
        config=PipelineConfig.default(),
    )


@pytest.fixture
def sample_polymarket_response() -> dict:
    """Standard Polymarket API response for mapper tests."""
    return {
        "id": "0x123abc",
        "question": "Will Red Sea shipping be disrupted?",
        "description": "Market resolves YES if...",
        "outcomePrices": ["0.75", "0.25"],
        "volume": "500000",
        "liquidity": "75000",
        "numTraders": 1200,
        "createdAt": "2024-01-15T10:00:00Z",
        "endDate": "2024-06-30T23:59:59Z",
    }


@pytest.fixture
def pipeline_with_dlq():
    """Pipeline with DLQ for testing error handling."""
    dlq = DeadLetterQueue()
    pipeline = OmenPipeline(
        validator=SignalValidator(
            rules=[LiquidityValidationRule(min_liquidity_usd=1000.0)]
        ),
        enricher=SignalEnricher(),
        repository=InMemorySignalRepository(),
        publisher=None,
        dead_letter_queue=dlq,
        config=PipelineConfig(
            ruleset_version=RulesetVersion("test"),
            target_domains=frozenset({ImpactDomain.LOGISTICS}),
            enable_dlq=True,
        ),
    )
    return pipeline, dlq


@pytest.fixture
def dry_run_pipeline():
    """Pipeline in dry-run mode with mocked repository and publisher."""
    repo = MagicMock()
    pub = MagicMock()
    return OmenPipeline(
        validator=SignalValidator(
            rules=[LiquidityValidationRule(min_liquidity_usd=100.0)]
        ),
        enricher=SignalEnricher(),
        repository=repo,
        publisher=pub,
        config=PipelineConfig(
            ruleset_version=RulesetVersion("test"),
            target_domains=frozenset({ImpactDomain.LOGISTICS}),
            enable_dry_run=True,
        ),
    )


@pytest.fixture
def async_pipeline() -> AsyncOmenPipeline:
    """Async pipeline for behavior testing."""
    return AsyncOmenPipeline(
        validator=SignalValidator(
            rules=[LiquidityValidationRule(min_liquidity_usd=1000.0)]
        ),
        enricher=SignalEnricher(),
        repository=AsyncInMemorySignalRepository(),
        publisher=None,
        config=PipelineConfig(
            ruleset_version=RulesetVersion("test"),
            target_domains=frozenset({ImpactDomain.LOGISTICS}),
        ),
        max_concurrent=5,
    )
