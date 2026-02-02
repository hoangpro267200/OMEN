"""Tests for validation rules."""

import pytest

from omen.domain.models.common import EventId, MarketId, ValidationStatus
from omen.domain.models.raw_signal import RawSignalEvent, MarketMetadata
from omen.domain.rules.validation.liquidity_rule import LiquidityValidationRule


def test_passes_when_liquidity_sufficient(high_quality_event):
    """LiquidityValidationRule passes when liquidity meets threshold."""
    rule = LiquidityValidationRule(min_liquidity_usd=1000.0)
    result = rule.apply(high_quality_event)
    assert result.status == ValidationStatus.PASSED
    assert result.score >= 0
    assert result.score <= 1
    assert "Sufficient liquidity" in result.reason


def test_rejects_when_liquidity_insufficient(low_liquidity_event):
    """LiquidityValidationRule rejects when liquidity is below threshold."""
    rule = LiquidityValidationRule(min_liquidity_usd=1000.0)
    result = rule.apply(low_liquidity_event)
    assert result.status == ValidationStatus.REJECTED_LOW_LIQUIDITY
    assert "Insufficient liquidity" in result.reason
    assert result.score < 1.0


def test_explanation_is_provided(high_quality_event):
    """Rule provides an explanation step for auditability."""
    rule = LiquidityValidationRule(min_liquidity_usd=1000.0)
    app_result = rule.apply(high_quality_event)
    step = rule.explain(high_quality_event, app_result)
    assert step.rule_name == "liquidity_validation"
    assert step.rule_version == "1.0.0"
    assert "current_liquidity_usd" in step.input_summary
    assert "threshold_usd" in step.input_summary
    assert step.output_summary.get("status") == ValidationStatus.PASSED.value
    assert step.reasoning
    # Registry-backed parameter citation when available
    assert len(step.parameters_used) >= 1
    assert step.parameters_used[0].name == "min_liquidity_usd"
    assert step.parameters_used[0].unit == "USD"


def test_deterministic_output(high_quality_event):
    """Same input produces the same validation result."""
    rule = LiquidityValidationRule(min_liquidity_usd=1000.0)
    r1 = rule.apply(high_quality_event)
    r2 = rule.apply(high_quality_event)
    assert r1.status == r2.status
    assert r1.score == r2.score
    assert r1.reason == r2.reason


def test_score_scales_with_liquidity():
    """Score increases with liquidity up to the cap."""
    rule = LiquidityValidationRule(min_liquidity_usd=1000.0)
    low = RawSignalEvent(
        event_id=EventId("e1"),
        title="Test",
        probability=0.5,
        market=MarketMetadata(
            source="t",
            market_id=MarketId("m1"),
            total_volume_usd=2000.0,
            current_liquidity_usd=2000.0,
        ),
    )
    high = RawSignalEvent(
        event_id=EventId("e2"),
        title="Test",
        probability=0.5,
        market=MarketMetadata(
            source="t",
            market_id=MarketId("m2"),
            total_volume_usd=50000.0,
            current_liquidity_usd=50000.0,
        ),
    )
    res_low = rule.apply(low)
    res_high = rule.apply(high)
    assert res_low.status == ValidationStatus.PASSED
    assert res_high.status == ValidationStatus.PASSED
    assert res_high.score >= res_low.score


def test_threshold_is_configurable(low_liquidity_event):
    """Threshold can be set so that the same event passes or fails."""
    strict = LiquidityValidationRule(min_liquidity_usd=10_000.0)
    loose = LiquidityValidationRule(min_liquidity_usd=10.0)
    assert strict.apply(low_liquidity_event).status == ValidationStatus.REJECTED_LOW_LIQUIDITY
    assert loose.apply(low_liquidity_event).status == ValidationStatus.PASSED
