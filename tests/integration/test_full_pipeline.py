"""Integration tests for full pipeline."""

import pytest

from omen.adapters.inbound.stub_source import StubSignalSource
from omen.adapters.outbound.console_publisher import ConsolePublisher
from omen.adapters.persistence.in_memory_repository import InMemorySignalRepository
from omen.application.pipeline import OmenPipeline, PipelineConfig
from omen.domain.services.signal_validator import SignalValidator
from omen.domain.services.signal_enricher import SignalEnricher
from omen.domain.rules.validation.liquidity_rule import LiquidityValidationRule


def test_full_pipeline_integration():
    """Test full pipeline with stub source and current components."""
    validator = SignalValidator(rules=[LiquidityValidationRule(min_liquidity_usd=1000.0)])
    enricher = SignalEnricher()
    repository = InMemorySignalRepository()
    publisher = ConsolePublisher()
    pipeline = OmenPipeline(
        validator=validator,
        enricher=enricher,
        repository=repository,
        publisher=publisher,
        config=PipelineConfig.default(),
    )

    source = StubSignalSource()
    results = []
    for event in source.fetch_events(limit=10):
        result = pipeline.process_single(event)
        results.append(result)

    assert len(results) > 0
    successful = [r for r in results if r.success and len(r.signals) > 0]
    assert len(successful) >= 1

    recent = repository.find_recent(limit=100)
    assert len(recent) >= len(successful)
