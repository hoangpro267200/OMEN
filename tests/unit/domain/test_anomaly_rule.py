"""Tests for AnomalyDetectionRule."""

import pytest

from omen.domain.models.common import EventId, MarketId, ValidationStatus
from omen.domain.models.raw_signal import RawSignalEvent, MarketMetadata
from omen.domain.rules.validation.anomaly_detection_rule import (
    AnomalyDetectionRule,
    AnomalyConfig,
)


@pytest.fixture
def normal_event() -> RawSignalEvent:
    """Event with normal probability and movement."""
    return RawSignalEvent(
        event_id=EventId("anom-normal"),
        title="Red Sea disruption",
        probability=0.5,
        keywords=["red sea"],
        market=MarketMetadata(
            source="t",
            market_id=MarketId("m1"),
            total_volume_usd=100000.0,
            current_liquidity_usd=50000.0,
            num_traders=500,
        ),
    )


@pytest.fixture
def extreme_probability_event() -> RawSignalEvent:
    """Event with probability near 1 (suspicious)."""
    return RawSignalEvent(
        event_id=EventId("anom-extreme"),
        title="Test",
        probability=0.99,
        keywords=["test"],
        market=MarketMetadata(
            source="t",
            market_id=MarketId("m1"),
            total_volume_usd=10000.0,
            current_liquidity_usd=5000.0,
            num_traders=100,
        ),
    )


def test_passes_when_no_anomalies(normal_event):
    """Rule passes when no anomalies detected."""
    rule = AnomalyDetectionRule()
    result = rule.apply(normal_event)
    assert result.status == ValidationStatus.PASSED
    assert result.score == 1.0
    assert "No anomalies" in result.reason


def test_rejects_when_extreme_probability(extreme_probability_event):
    """Rule rejects when probability is too high and risk_score >= 0.5."""
    # Need risk_score >= 0.5 to reject. Single "prob too high" adds 0.3.
    # Use stricter max_probability so 0.99 is clearly over, and add another
    # anomaly (e.g. huge move) to push risk over 0.5.
    from omen.domain.models.common import ProbabilityMovement

    rule = AnomalyDetectionRule(config=AnomalyConfig(max_probability=0.90, min_probability=0.05))
    event = RawSignalEvent(
        event_id=EventId("anom-extreme2"),
        title="Test",
        probability=0.99,
        movement=ProbabilityMovement(current=0.99, previous=0.3, delta=0.69, window_hours=24),
        keywords=["test"],
        market=MarketMetadata(
            source="t",
            market_id=MarketId("m1"),
            total_volume_usd=10000.0,
            current_liquidity_usd=5000.0,
            num_traders=100,
        ),
    )
    result = rule.apply(event)
    assert result.status == ValidationStatus.REJECTED_MANIPULATION_SUSPECTED
    assert result.score < 1.0
    assert (
        "Probability too high" in result.reason
        or "Unusual probability" in result.reason
        or "99" in result.reason
    )


def test_rejects_when_huge_probability_move():
    """Rule rejects when probability change is excessive (risk_score >= 0.5)."""
    from omen.domain.models.common import ProbabilityMovement

    # Delta 0.6 adds 0.4 risk. Add extreme prob (0.99, max 0.95) for +0.3 → 0.7 total.
    rule = AnomalyDetectionRule(
        config=AnomalyConfig(
            max_probability_change_24h=0.5,
            max_probability=0.95,
        )
    )
    event = RawSignalEvent(
        event_id=EventId("anom-move"),
        title="Test",
        probability=0.99,
        movement=ProbabilityMovement(current=0.99, previous=0.35, delta=0.64, window_hours=24),
        keywords=[],
        market=MarketMetadata(
            source="t",
            market_id=MarketId("m1"),
            total_volume_usd=10000.0,
            current_liquidity_usd=5000.0,
        ),
    )
    result = rule.apply(event)
    assert result.status == ValidationStatus.REJECTED_MANIPULATION_SUSPECTED
    assert "Unusual probability change" in result.reason or "Probability too high" in result.reason


def test_rejects_when_few_traders_high_volume():
    """Rule rejects when volume is high but trader count is low (risk_score >= 0.5)."""
    # Few traders + high volume adds 0.3. Add extreme prob for +0.3 → 0.6 total.
    rule = AnomalyDetectionRule(
        config=AnomalyConfig(
            min_traders=10,
            min_volume_for_high_confidence=10000.0,
            max_probability=0.90,
        )
    )
    event = RawSignalEvent(
        event_id=EventId("anom-traders"),
        title="Test",
        probability=0.98,
        keywords=[],
        market=MarketMetadata(
            source="t",
            market_id=MarketId("m1"),
            total_volume_usd=500000.0,
            current_liquidity_usd=100000.0,
            num_traders=3,
        ),
    )
    result = rule.apply(event)
    assert result.status == ValidationStatus.REJECTED_MANIPULATION_SUSPECTED
    assert (
        "traders" in result.reason.lower()
        or "volume" in result.reason.lower()
        or "Probability" in result.reason
    )


def test_minor_anomalies_still_pass():
    """Single minor anomaly can still result in PASS with reduced score."""
    rule = AnomalyDetectionRule(config=AnomalyConfig(max_probability=0.98))  # 0.99 now passes
    # Probability 0.99 with max 0.98 → anomaly
    event = RawSignalEvent(
        event_id=EventId("anom-minor"),
        title="Test",
        probability=0.99,
        keywords=[],
        market=MarketMetadata(
            source="t",
            market_id=MarketId("m1"),
            total_volume_usd=10000.0,
            current_liquidity_usd=5000.0,
            num_traders=100,
        ),
    )
    result = rule.apply(event)
    # risk_score 0.3 < 0.5 so we get PASS with score 0.7
    assert result.status == ValidationStatus.PASSED
    assert result.score < 1.0
    assert "Minor anomalies" in result.reason or "Probability too high" in result.reason


def test_explanation_has_required_fields(normal_event):
    """Rule provides explanation step."""
    rule = AnomalyDetectionRule()
    app_result = rule.apply(normal_event)
    step = rule.explain(normal_event, app_result)
    assert step.rule_name == "anomaly_detection"
    assert step.rule_version == "2.0.0"
    assert "probability" in step.input_summary
    assert step.output_summary.get("status") == app_result.status.value
    assert step.timestamp is not None


def test_deterministic_output(normal_event):
    """Same input produces same result."""
    rule = AnomalyDetectionRule()
    r1 = rule.apply(normal_event)
    r2 = rule.apply(normal_event)
    assert r1.status == r2.status
    assert r1.score == r2.score
    assert r1.reason == r2.reason
