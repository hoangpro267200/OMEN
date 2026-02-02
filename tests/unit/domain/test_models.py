"""Tests for domain models (current schema)."""

from datetime import datetime

import pytest

from omen.domain.models.common import (
    EventId,
    MarketId,
    SignalCategory,
    ValidationStatus,
    RulesetVersion,
    generate_deterministic_hash,
)
from omen.domain.models.raw_signal import RawSignalEvent, MarketMetadata
from omen.domain.models.validated_signal import ValidatedSignal, ValidationResult
from omen.domain.models.context import ProcessingContext
from omen.domain.models.explanation import ExplanationChain, ExplanationStep


def test_raw_signal_creation():
    """Test RawSignalEvent creation with required fields."""
    event = RawSignalEvent(
        event_id=EventId("test-1"),
        title="Test event",
        probability=0.5,
        market=MarketMetadata(
            source="test",
            market_id=MarketId("m1"),
            total_volume_usd=1000.0,
            current_liquidity_usd=500.0,
        ),
    )
    assert event.event_id == "test-1"
    assert event.probability == 0.5
    assert event.input_event_hash
    assert len(event.input_event_hash) == 16


def test_validated_signal_creation(high_quality_event, ruleset_version, processing_context):
    """Test ValidatedSignal creation with current schema."""
    step = ExplanationStep.create(
        step_id=1,
        rule_name="liquidity_validation",
        rule_version="1.0.0",
        reasoning="OK",
        confidence_contribution=0.3,
        processing_time=processing_context.processing_time,
        input_summary={"liquidity": 1000.0},
        output_summary={"status": "PASSED"},
    )
    chain = ExplanationChain.create(processing_context).add_step(step).finalize(processing_context)
    signal = ValidatedSignal(
        event_id=high_quality_event.event_id,
        original_event=high_quality_event,
        category=SignalCategory.GEOPOLITICAL,
        affected_chokepoints=["Red Sea"],
        validation_results=[
            ValidationResult(
                rule_name="liquidity_validation",
                rule_version="1.0.0",
                status=ValidationStatus.PASSED,
                score=0.9,
                reason="OK",
            )
        ],
        overall_validation_score=0.9,
        signal_strength=0.9,
        liquidity_score=0.9,
        explanation=chain,
        ruleset_version=ruleset_version,
    )
    assert signal.overall_validation_score >= 0.0 and signal.overall_validation_score <= 1.0
    assert signal.validation_passed
    assert signal.deterministic_trace_id


def test_explanation_step():
    """Test ExplanationStep creation (current schema)."""
    t = datetime(2025, 1, 15, 12, 0, 0)
    step = ExplanationStep(
        step_id=1,
        rule_name="test_rule",
        rule_version="1.0.0",
        input_summary={"x": 1},
        output_summary={"y": 2},
        reasoning="Because",
        confidence_contribution=0.9,
        timestamp=t,
    )
    assert step.rule_name == "test_rule"
    assert step.confidence_contribution == 0.9
