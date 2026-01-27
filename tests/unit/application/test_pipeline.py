"""Tests for OmenPipeline."""

import pytest

from omen.application.pipeline import OmenPipeline, PipelineConfig
from omen.domain.services.signal_validator import SignalValidator
from omen.domain.services.impact_translator import ImpactTranslator
from omen.domain.rules.validation.liquidity_rule import LiquidityValidationRule
from omen.domain.rules.translation.logistics.red_sea_disruption import RedSeaDisruptionRule
from omen.adapters.persistence.in_memory_repository import InMemorySignalRepository
from omen.adapters.outbound.console_publisher import ConsolePublisher


def test_process_single_valid_event(pipeline, high_quality_event):
    """Pipeline processes a valid event and produces signals."""
    result = pipeline.process_single(high_quality_event)
    assert result.success is True
    assert len(result.signals) >= 1
    assert result.error is None
    assert result.stats.events_received == 1


def test_process_single_invalid_event_rejected(pipeline, low_liquidity_event):
    """Pipeline rejects an event that fails validation (e.g. low liquidity)."""
    result = pipeline.process_single(low_liquidity_event)
    assert result.success is True  # pipeline completed, no crash
    assert len(result.signals) == 0
    assert len(result.validation_failures) >= 1
    assert result.stats.events_rejected_validation >= 1


def test_process_batch_mixed_events(pipeline, high_quality_event, low_liquidity_event):
    """Pipeline processes a batch of mixed valid/invalid events."""
    results = pipeline.process_batch([high_quality_event, low_liquidity_event])
    assert len(results) == 2
    valid_results = [r for r in results if r.success and r.signals]
    reject_results = [r for r in results if r.success and not r.signals and r.validation_failures]
    assert len(valid_results) >= 1
    assert len(reject_results) >= 1


def test_idempotency_returns_cached_result(pipeline, high_quality_event):
    """Processing the same event twice returns cached result on second run."""
    r1 = pipeline.process_single(high_quality_event)
    r2 = pipeline.process_single(high_quality_event)
    assert r1.success and r2.success
    assert len(r1.signals) >= 1 and len(r2.signals) >= 1
    assert r2.cached is True
    assert r1.signals[0].signal_id == r2.signals[0].signal_id


def test_pipeline_produces_omen_signal(pipeline, high_quality_event):
    """Pipeline output contains OmenSignal instances."""
    result = pipeline.process_single(high_quality_event)
    assert result.success
    assert len(result.signals) >= 1
    from omen.domain.models.omen_signal import OmenSignal
    for s in result.signals:
        assert isinstance(s, OmenSignal)


def test_omen_signal_has_required_fields(pipeline, high_quality_event):
    """Each OmenSignal has the required identity and explanation fields."""
    result = pipeline.process_single(high_quality_event)
    assert result.success and result.signals
    s = result.signals[0]
    assert s.signal_id
    assert s.event_id
    assert s.input_event_hash
    assert s.deterministic_trace_id
    assert s.ruleset_version
    assert s.title
    assert s.summary
    assert s.detailed_explanation
    assert s.explanation_chain
    assert 0 <= s.confidence_score <= 1
    assert 0 <= s.severity <= 1


def test_deterministic_trace_id_is_stable(pipeline, high_quality_event):
    """Same event produces the same deterministic_trace_id across runs."""
    r1 = pipeline.process_single(high_quality_event)
    r2 = pipeline.process_single(high_quality_event)
    assert r1.signals and r2.signals
    assert r1.signals[0].deterministic_trace_id == r2.signals[0].deterministic_trace_id
