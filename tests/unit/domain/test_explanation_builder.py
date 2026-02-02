"""Tests for ExplanationBuilder and ChainBuilder."""

from datetime import datetime

import pytest

from omen.domain.models.common import RulesetVersion
from omen.domain.models.context import ProcessingContext
from omen.domain.models.explanation import (
    ExplanationChain,
    ExplanationStep,
    ParameterReference,
)
from omen.domain.services.explanation_builder import ChainBuilder, ExplanationBuilder


@pytest.fixture
def processing_context() -> ProcessingContext:
    """Fixed-time processing context for deterministic tests."""
    return ProcessingContext.create_for_replay(
        processing_time=datetime(2025, 1, 15, 12, 0, 0),
        ruleset_version=RulesetVersion("test-v1.0.0"),
    )


def test_explanation_builder_builds_step_with_parameters(
    processing_context: ProcessingContext,
) -> None:
    """ExplanationBuilder produces a step with parameters_used and correct structure."""
    step = (
        ExplanationBuilder(processing_context, step_id=1)
        .for_rule("red_sea_disruption_logistics", "2.0.0")
        .with_input("probability", 0.75)
        .with_output("transit_increase", 7.5, "days")
        .used_parameter("reroute_transit_days", 10, "days", source="Drewry 2024")
        .with_reasoning(
            "Red Sea disruption at {probability:.0%} adds {transit_increase} days transit"
        )
        .with_confidence(0.8)
        .build()
    )
    assert step.step_id == 1
    assert step.rule_name == "red_sea_disruption_logistics"
    assert step.rule_version == "2.0.0"
    assert step.input_summary == {"probability": 0.75}
    assert step.output_summary == {"transit_increase": {"value": 7.5, "unit": "days"}}
    assert len(step.parameters_used) == 1
    assert step.parameters_used[0].name == "reroute_transit_days"
    assert step.parameters_used[0].value == 10
    assert step.parameters_used[0].unit == "days"
    assert step.parameters_used[0].source == "Drewry 2024"
    assert step.reasoning == "Red Sea disruption at 75% adds 7.5 days transit"
    assert step.confidence_contribution == 0.8
    assert step.timestamp == processing_context.processing_time
    assert step.duration_ms is not None


def test_explanation_builder_to_human_readable(
    processing_context: ProcessingContext,
) -> None:
    """Step built by ExplanationBuilder produces correct to_human_readable output."""
    step = (
        ExplanationBuilder(processing_context, step_id=1)
        .for_rule("liquidity_validation", "1.0.0")
        .with_input("liquidity", 5000.0)
        .used_parameter("min_liquidity_usd", 1000.0, "USD", source="Config")
        .with_reasoning("Liquidity {liquidity} above threshold")
        .with_confidence(0.9)
        .build()
    )
    text = step.to_human_readable()
    assert "Step 1: liquidity_validation (v1.0.0)" in text
    assert "Liquidity 5000.0 above threshold" in text
    assert "Parameters:" in text
    assert "min_liquidity_usd: 1000.0 USD" in text
    assert "Source: Config" in text
    assert "Confidence contribution: 90%" in text


def test_explanation_builder_to_audit_format(
    processing_context: ProcessingContext,
) -> None:
    """Step built by ExplanationBuilder produces correct to_audit_format output."""
    step = (
        ExplanationBuilder(processing_context, step_id=1)
        .for_rule("test_rule", "1.0.0")
        .with_reasoning("Test reasoning")
        .with_confidence(0.5)
        .build()
    )
    audit = step.to_audit_format()
    assert audit["step_id"] == 1
    assert audit["rule"] == "test_rule@1.0.0"
    assert audit["inputs"] == {}
    assert audit["outputs"] == {}
    assert audit["parameters"] == []
    assert audit["reasoning"] == "Test reasoning"
    assert audit["confidence"] == 0.5
    assert "timestamp" in audit


def test_explanation_builder_requires_rule_and_reasoning(
    processing_context: ProcessingContext,
) -> None:
    """Builder raises if rule or reasoning is missing."""
    with pytest.raises(ValueError, match="Rule name and version required"):
        (
            ExplanationBuilder(processing_context, step_id=1)
            .with_reasoning("x")
            .with_confidence(0.5)
            .build()
        )
    with pytest.raises(ValueError, match="Reasoning required"):
        (
            ExplanationBuilder(processing_context, step_id=1)
            .for_rule("r", "1.0")
            .with_confidence(0.5)
            .build()
        )


def test_chain_builder_builds_chain(
    processing_context: ProcessingContext,
) -> None:
    """ChainBuilder produces an ExplanationChain with multiple steps."""
    step1 = (
        ExplanationBuilder(processing_context, step_id=1)
        .for_rule("rule_a", "1.0")
        .with_reasoning("First step")
        .with_confidence(0.8)
        .build()
    )
    step2 = (
        ExplanationBuilder(processing_context, step_id=2)
        .for_rule("rule_b", "1.0")
        .with_reasoning("Second step")
        .with_confidence(0.7)
        .build()
    )
    chain = ChainBuilder(processing_context).add_step(step1).add_step(step2).build()
    assert isinstance(chain, ExplanationChain)
    assert chain.trace_id == processing_context.trace_id
    assert chain.total_steps == 2
    assert chain.steps[0].rule_name == "rule_a"
    assert chain.steps[1].rule_name == "rule_b"
    assert chain.completed_at == processing_context.processing_time


def test_chain_builder_new_step_increments_id(
    processing_context: ProcessingContext,
) -> None:
    """new_step() returns a builder with the next step_id."""
    cb = ChainBuilder(processing_context)
    b1 = cb.new_step()
    step1 = b1.for_rule("a", "1").with_reasoning("x").with_confidence(0.5).build()
    assert step1.step_id == 1
    cb.add_step(step1)
    b2 = cb.new_step()
    step2 = b2.for_rule("b", "1").with_reasoning("y").with_confidence(0.5).build()
    assert step2.step_id == 2
