"""Tests for translation rules."""

from datetime import datetime

import pytest

from omen.domain.models.common import (
    EventId,
    MarketId,
    RulesetVersion,
    SignalCategory,
    ValidationStatus,
)
from omen.domain.models.raw_signal import RawSignalEvent, MarketMetadata
from omen.domain.models.validated_signal import ValidatedSignal, ValidationResult
from omen.domain.models.context import ProcessingContext
from omen.domain.models.explanation import ExplanationChain, ExplanationStep
from omen_impact.rules.logistics import RedSeaDisruptionRule

_FIXED_TIME = datetime(2025, 1, 15, 12, 0, 0)


def _make_validated_signal(
    event: RawSignalEvent,
    category: SignalCategory,
    chokepoints: list[str],
    keywords: list[str] | None = None,
) -> ValidatedSignal:
    """Build a ValidatedSignal from an event and classification."""
    ctx = ProcessingContext.create_for_replay(
        processing_time=_FIXED_TIME,
        ruleset_version=RulesetVersion("test-v1"),
    )
    step = ExplanationStep.create(
        step_id=1,
        rule_name="liquidity_validation",
        rule_version="1.0.0",
        reasoning="Sufficient liquidity",
        confidence_contribution=0.27,
        processing_time=ctx.processing_time,
        input_summary={"current_liquidity_usd": event.market.current_liquidity_usd},
        output_summary={"status": "PASSED", "score": 0.9},
    )
    chain = ExplanationChain.create(ctx).add_step(step).finalize(ctx)
    return ValidatedSignal(
        event_id=event.event_id,
        original_event=event,
        category=category,
        relevant_locations=event.inferred_locations,
        affected_chokepoints=chokepoints,
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
        ruleset_version=RulesetVersion("test-v1"),
        validated_at=ctx.processing_time,
    )


def test_rule_is_applicable_for_red_sea_signals(validated_red_sea_signal):
    """RedSeaDisruptionRule is applicable for Red Sea–related validated signals."""
    rule = RedSeaDisruptionRule()
    assert rule.is_applicable(validated_red_sea_signal) is True


def test_rule_not_applicable_for_unrelated_signals(irrelevant_event):
    """RedSeaDisruptionRule is not applicable for unrelated signals."""
    validated = _make_validated_signal(
        irrelevant_event,
        category=SignalCategory.CLIMATE,
        chokepoints=[],
        keywords=irrelevant_event.keywords,
    )
    rule = RedSeaDisruptionRule()
    assert rule.is_applicable(validated) is False


def test_produces_logistics_metrics(validated_red_sea_signal):
    """Rule produces logistics-related impact metrics."""
    rule = RedSeaDisruptionRule()
    result = rule.translate(validated_red_sea_signal)
    assert result.applicable is True
    assert len(result.metrics) >= 1
    names = {m.name for m in result.metrics}
    assert "transit_time_increase" in names or any("transit" in n for n in names)
    assert any("fuel" in n for n in names) or any("freight" in n for n in names)


def test_affected_routes_are_identified(validated_red_sea_signal):
    """Rule identifies affected routes."""
    rule = RedSeaDisruptionRule()
    result = rule.translate(validated_red_sea_signal)
    assert result.applicable is True
    assert len(result.affected_routes) >= 1
    for r in result.affected_routes:
        assert r.route_id
        assert r.route_name
        assert 0 <= r.impact_severity <= 1


def test_affected_systems_are_identified(validated_red_sea_signal):
    """Rule identifies affected systems (e.g. Suez Canal)."""
    rule = RedSeaDisruptionRule()
    result = rule.translate(validated_red_sea_signal)
    assert result.applicable is True
    assert len(result.affected_systems) >= 1
    names = [s.system_name for s in result.affected_systems]
    assert any("Suez" in n for n in names)


def test_assumptions_are_explicit(validated_red_sea_signal):
    """Rule documents explicit assumptions."""
    rule = RedSeaDisruptionRule()
    result = rule.translate(validated_red_sea_signal)
    assert result.applicable is True
    assert len(result.assumptions) >= 1
    text = " ".join(result.assumptions).lower()
    assert "cape" in text or "rerout" in text or "fuel" in text or "probability" in text


def test_explanation_step_is_provided(validated_red_sea_signal):
    """Rule provides an explanation step for auditability."""
    rule = RedSeaDisruptionRule()
    result = rule.translate(validated_red_sea_signal)
    assert result.applicable is True
    assert result.explanation is not None
    assert result.explanation.rule_name == "red_sea_disruption_logistics"
    assert result.explanation.reasoning


def test_severity_scales_with_probability(validated_red_sea_signal):
    """Severity contribution increases with event probability."""
    rule = RedSeaDisruptionRule()
    base = validated_red_sea_signal.original_event
    low_ev = base.model_copy(update={"probability": 0.2})
    high_ev = base.model_copy(update={"probability": 0.9})
    low_sig = _make_validated_signal(
        low_ev, validated_red_sea_signal.category, validated_red_sea_signal.affected_chokepoints
    )
    high_sig = _make_validated_signal(
        high_ev, validated_red_sea_signal.category, validated_red_sea_signal.affected_chokepoints
    )
    r_low = rule.translate(low_sig)
    r_high = rule.translate(high_sig)
    assert r_low.applicable and r_high.applicable
    assert r_high.severity_contribution >= r_low.severity_contribution


def test_deterministic_output(validated_red_sea_signal):
    """Same input produces the same translation result."""
    rule = RedSeaDisruptionRule()
    r1 = rule.translate(validated_red_sea_signal)
    r2 = rule.translate(validated_red_sea_signal)
    assert r1.applicable == r2.applicable
    assert len(r1.metrics) == len(r2.metrics)
    for m1, m2 in zip(r1.metrics, r2.metrics):
        assert m1.name == m2.name and m1.value == m2.value
    assert r1.severity_contribution == r2.severity_contribution
