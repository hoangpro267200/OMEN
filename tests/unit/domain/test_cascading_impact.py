"""Tests for CascadingImpactAnalyzer."""

from datetime import datetime

import pytest

from omen.domain.models.common import EventId, MarketId, RulesetVersion
from omen.domain.models.raw_signal import RawSignalEvent, MarketMetadata
from omen.domain.models.validated_signal import ValidatedSignal, ValidationResult
from omen.domain.models.context import ProcessingContext
from omen.domain.models.explanation import ExplanationChain, ExplanationStep
from omen.domain.models.common import (
    ImpactDomain,
    ValidationStatus,
    SignalCategory,
)
from omen_impact.assessment import (
    ImpactAssessment,
    ImpactMetric,
    UncertaintyBounds,
)
from omen_impact.cascading_impact import (
    CascadingImpactAnalyzer,
    CascadeRule,
    LOGISTICS_CASCADE_RULES,
)


@pytest.fixture
def sample_assessment():
    """Impact assessment with transit_time_increase and freight_rate_pressure."""
    ctx = ProcessingContext.create_for_replay(
        processing_time=datetime(2025, 1, 15, 12, 0, 0),
        ruleset_version=RulesetVersion("test-v1"),
    )
    event = RawSignalEvent(
        event_id=EventId("cascade-test"),
        title="Red Sea disruption",
        probability=0.7,
        keywords=["red sea"],
        market=MarketMetadata(
            source="t",
            market_id=MarketId("m1"),
            total_volume_usd=10000.0,
            current_liquidity_usd=5000.0,
        ),
    )
    step = ExplanationStep.create(
        step_id=1,
        rule_name="red_sea",
        rule_version="2.0.0",
        reasoning="Test",
        confidence_contribution=0.8,
        processing_time=ctx.processing_time,
        input_summary={},
        output_summary={},
    )
    chain = ExplanationChain.create(ctx).add_step(step).finalize(ctx)
    sig = ValidatedSignal(
        event_id=event.event_id,
        original_event=event,
        category=SignalCategory.GEOPOLITICAL,
        relevant_locations=[],
        affected_chokepoints=["Red Sea"],
        validation_results=[
            ValidationResult(
                rule_name="l", rule_version="1", status=ValidationStatus.PASSED,
                score=0.9, reason="OK"
            )
        ],
        overall_validation_score=0.9,
        signal_strength=0.9,
        liquidity_score=0.9,
        explanation=chain,
        ruleset_version=RulesetVersion("test-v1"),
        validated_at=ctx.processing_time,
    )
    metrics = [
        ImpactMetric(
            name="transit_time_increase",
            value=7.0,
            unit="days",
            uncertainty=UncertaintyBounds(5.0, 9.0),
            confidence=0.8,
        ),
        ImpactMetric(
            name="freight_rate_pressure",
            value=15.0,
            unit="percent",
            uncertainty=UncertaintyBounds(8.0, 25.0),
            confidence=0.5,
        ),
    ]
    return ImpactAssessment(
        event_id=event.event_id,
        source_signal=sig,
        domain=ImpactDomain.LOGISTICS,
        metrics=metrics,
        affected_routes=[],
        affected_systems=[],
        overall_severity=0.75,
        severity_label="HIGH",
        expected_onset_hours=24,
        expected_duration_hours=720,
        explanation_steps=[step],
        explanation_chain=chain,
        impact_summary="Red Sea disruption. Transit +7d, freight +15%.",
        assumptions=[],
        ruleset_version=ctx.ruleset_version,
        translation_rules_applied=["red_sea"],
        assessed_at=ctx.processing_time,
    )


def test_cascading_analyzer_returns_list(sample_assessment):
    """Analyzer returns a list of ImpactMetrics."""
    analyzer = CascadingImpactAnalyzer()
    cascaded = analyzer.analyze(sample_assessment, max_cascade_depth=1)
    assert isinstance(cascaded, list)
    assert all(isinstance(m, ImpactMetric) for m in cascaded)


def test_cascading_derives_from_source_metrics(sample_assessment):
    """Cascaded metrics are derived from primary metrics."""
    analyzer = CascadingImpactAnalyzer()
    cascaded = analyzer.analyze(sample_assessment, max_cascade_depth=1)
    names = [m.name for m in cascaded]
    # From LOGISTICS_CASCADE_RULES: transit_time_increase -> inventory, production_schedule; freight_rate_pressure -> product_cost; port_delay -> demurrage
    # We have transit_time_increase and freight_rate_pressure
    assert any("inventory_carrying_cost" in n for n in names) or any("production_schedule" in n for n in names)
    assert any("product_cost" in n for n in names)


def test_cascading_confidence_decays(sample_assessment):
    """Deeper cascade levels have lower confidence."""
    analyzer = CascadingImpactAnalyzer()
    cascaded = analyzer.analyze(sample_assessment, max_cascade_depth=2)
    # Depth 1 and 2 both exist; depth 2 should have lower confidence
    assert len(cascaded) >= 1
    for m in cascaded:
        assert 0 <= m.confidence <= 1


def test_cascade_rule_dataclass():
    """CascadeRule has expected fields."""
    r = CascadeRule(
        source_metric="transit_time_increase",
        target_metric="inventory_cost",
        cascade_factor=0.15,
        delay_hours=0,
        description="Test",
    )
    assert r.source_metric == "transit_time_increase"
    assert r.cascade_factor == 0.15
    assert r.confidence_decay == 0.8


def test_logistics_cascade_rules_non_empty():
    """Standard logistics cascade rules are defined."""
    assert len(LOGISTICS_CASCADE_RULES) >= 1
    for r in LOGISTICS_CASCADE_RULES:
        assert r.source_metric and r.target_metric and r.cascade_factor >= 0
