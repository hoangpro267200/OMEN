"""Tests for explanation report generators."""

from datetime import datetime

import pytest

from omen.domain.models.common import (
    ConfidenceLevel,
    EventId,
    ImpactDomain,
    RulesetVersion,
    SignalCategory,
)
from omen.domain.models.explanation import ExplanationChain, ExplanationStep
from omen.domain.models.context import ProcessingContext
from omen.domain.models.impact_assessment import AffectedRoute, ImpactMetric
from omen.domain.models.omen_signal import OmenSignal
from omen.domain.services.explanation_report import (
    generate_json_audit_report,
    generate_text_report,
)


def _minimal_signal(
    explanation_chain: ExplanationChain,
    key_metrics: list[ImpactMetric] | None = None,
    affected_routes: list[AffectedRoute] | None = None,
) -> OmenSignal:
    """Build a minimal OmenSignal for report tests."""
    return OmenSignal(
        signal_id="OMEN-TEST001",
        event_id=EventId("ev-1"),
        category=SignalCategory.GEOPOLITICAL,
        subcategory=None,
        domain=ImpactDomain.LOGISTICS,
        current_probability=0.75,
        probability_momentum="STABLE",
        probability_change_24h=None,
        confidence_level=ConfidenceLevel.HIGH,
        confidence_score=0.85,
        confidence_factors={"liquidity": 0.9, "validation": 0.8},
        severity=0.7,
        severity_label="HIGH",
        key_metrics=key_metrics or [],
        affected_routes=affected_routes or [],
        affected_systems=[],
        affected_regions=[],
        expected_onset_hours=24,
        expected_duration_hours=168,
        title="Test signal title",
        summary="Short summary of the signal for display (at least 10 chars).",
        detailed_explanation="Longer explanation of reasoning and assumptions (at least 10 characters).",
        explanation_chain=explanation_chain,
        input_event_hash="abc123",
        ruleset_version=RulesetVersion("v1.0.0"),
        deterministic_trace_id="trace-xyz",
        source_market="test",
        market_url="https://example.com/m",
        generated_at=datetime(2025, 1, 15, 12, 0, 0),
    )


@pytest.fixture
def processing_context() -> ProcessingContext:
    return ProcessingContext.create_for_replay(
        processing_time=datetime(2025, 1, 15, 12, 0, 0),
        ruleset_version=RulesetVersion("v1.0.0"),
    )


def test_generate_text_report_contains_sections(processing_context: ProcessingContext) -> None:
    """generate_text_report includes summary, reasoning chain, and reproducibility."""
    step = ExplanationStep.create(
        step_id=1,
        rule_name="liquidity_validation",
        rule_version="1.0.0",
        reasoning="Sufficient liquidity",
        confidence_contribution=0.3,
        processing_time=processing_context.processing_time,
    )
    chain = (
        ExplanationChain.create(processing_context)
        .add_step(step)
        .finalize(processing_context)
    )
    signal = _minimal_signal(chain)
    report = generate_text_report(signal)
    assert "OMEN SIGNAL REPORT: OMEN-TEST001" in report
    assert "SUMMARY" in report
    assert "Title: Test signal title" in report
    assert "Confidence:" in report
    assert "REASONING CHAIN" in report
    assert "Step 1: liquidity_validation" in report
    assert "Sufficient liquidity" in report
    assert "REPRODUCIBILITY" in report
    assert "Input Hash: abc123" in report
    assert "Trace ID: trace-xyz" in report
    assert "Ruleset: v1.0.0" in report


def test_generate_text_report_includes_metrics_and_routes(
    processing_context: ProcessingContext,
) -> None:
    """generate_text_report includes key_metrics and affected_routes when present."""
    chain = (
        ExplanationChain.create(processing_context)
        .add_step(
            ExplanationStep.create(
                step_id=1,
                rule_name="r",
                rule_version="1",
                reasoning="Ok",
                confidence_contribution=0.5,
                processing_time=processing_context.processing_time,
            )
        )
        .finalize(processing_context)
    )
    metric = ImpactMetric(
        name="Transit delay",
        value=10.0,
        unit="days",
        confidence=0.8,
        evidence_type="historical",
        evidence_source="Drewry 2024",
    )
    route = AffectedRoute(
        route_id="r1",
        route_name="Asia-Europe",
        origin_region="Asia",
        destination_region="Europe",
        impact_severity=0.75,
    )
    signal = _minimal_signal(chain, key_metrics=[metric], affected_routes=[route])
    report = generate_text_report(signal)
    assert "KEY METRICS" in report
    assert "Transit delay: 10.0 days" in report
    assert "Source: Drewry 2024" in report
    assert "AFFECTED ROUTES" in report
    assert "Asia-Europe" in report
    assert "Asia → Europe" in report
    assert "Severity: 75%" in report


def test_generate_json_audit_report_structure(processing_context: ProcessingContext) -> None:
    """generate_json_audit_report returns expected top-level and explanation_chain structure."""
    chain = (
        ExplanationChain.create(processing_context)
        .add_step(
            ExplanationStep.create(
                step_id=1,
                rule_name="test_rule",
                rule_version="1.0",
                reasoning="Test",
                confidence_contribution=0.6,
                processing_time=processing_context.processing_time,
            )
        )
        .finalize(processing_context)
    )
    signal = _minimal_signal(chain)
    out = generate_json_audit_report(signal)
    assert out["signal_id"] == "OMEN-TEST001"
    assert out["event_id"] == "ev-1"
    assert "reproducibility" in out
    assert out["reproducibility"]["input_event_hash"] == "abc123"
    assert out["reproducibility"]["ruleset_version"] == "v1.0.0"
    assert "classification" in out
    assert "assessment" in out
    assert "metrics" in out
    assert "affected_infrastructure" in out
    assert "explanation_chain" in out
    assert out["explanation_chain"]["trace_id"] == chain.trace_id
    assert out["explanation_chain"]["total_steps"] == 1
    assert len(out["explanation_chain"]["steps"]) == 1
    assert out["explanation_chain"]["steps"][0]["rule"] == "test_rule@1.0"
    assert out["explanation_chain"]["steps"][0]["reasoning"] == "Test"
    assert "source" in out
    assert "timestamps" in out
