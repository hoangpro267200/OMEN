"""Tests for GeographicRelevanceRule."""

import pytest

from omen.domain.models.common import EventId, MarketId, ValidationStatus, GeoLocation
from omen.domain.models.raw_signal import RawSignalEvent, MarketMetadata
from omen.domain.rules.validation.geographic_relevance_rule import (
    GeographicRelevanceRule,
    GeographicRelevanceConfig,
    CHOKEPOINTS,
)


@pytest.fixture
def red_sea_event() -> RawSignalEvent:
    """Event with Red Sea keywords and location."""
    return RawSignalEvent(
        event_id=EventId("geo-red-1"),
        title="Red Sea shipping disruption",
        description="Houthi attacks in Yemen",
        probability=0.6,
        keywords=["red sea", "houthi", "yemen", "suez"],
        inferred_locations=[
            GeoLocation(latitude=15.5, longitude=42.5, name="Red Sea", region_code="YE")
        ],
        market=MarketMetadata(
            source="t", market_id=MarketId("m1"),
            total_volume_usd=10000.0, current_liquidity_usd=5000.0,
        ),
    )


@pytest.fixture
def irrelevant_geo_event() -> RawSignalEvent:
    """Event with no logistics chokepoint relevance."""
    return RawSignalEvent(
        event_id=EventId("geo-irr-1"),
        title="Will it rain in Tokyo next week?",
        description="Weather prediction.",
        probability=0.3,
        keywords=["weather", "rain", "tokyo"],
        market=MarketMetadata(
            source="t", market_id=MarketId("m2"),
            total_volume_usd=10000.0, current_liquidity_usd=5000.0,
        ),
    )


def test_passes_when_keywords_match_chokepoint(red_sea_event):
    """Rule passes when event keywords match chokepoint terms."""
    rule = GeographicRelevanceRule()
    result = rule.apply(red_sea_event)
    assert result.status == ValidationStatus.PASSED
    assert result.score >= 0.4
    assert "Red Sea" in result.reason or "red sea" in result.reason.lower()
    assert "chokepoint" in result.reason.lower() or "suez" in result.reason.lower()


def test_rejects_when_no_geographic_relevance(irrelevant_geo_event):
    """Rule rejects when no chokepoint keywords or proximity."""
    rule = GeographicRelevanceRule()
    result = rule.apply(irrelevant_geo_event)
    assert result.status == ValidationStatus.REJECTED_IRRELEVANT_GEOGRAPHY
    assert result.score <= 0.2
    assert "No geographic relevance" in result.reason


def test_passes_when_location_near_chokepoint():
    """Rule passes when inferred location is within proximity of a chokepoint."""
    # Location very close to Red Sea chokepoint (20, 38)
    rule = GeographicRelevanceRule(
        config=GeographicRelevanceConfig(proximity_threshold_km=500.0)
    )
    event = RawSignalEvent(
        event_id=EventId("geo-loc-1"),
        title="Regional tension",
        probability=0.5,
        keywords=[],
        inferred_locations=[
            GeoLocation(latitude=20.5, longitude=38.2, name="Near Red Sea")
        ],
        market=MarketMetadata(
            source="t", market_id=MarketId("m1"),
            total_volume_usd=10000.0, current_liquidity_usd=5000.0,
        ),
    )
    result = rule.apply(event)
    assert result.status == ValidationStatus.PASSED
    assert "Red Sea" in result.reason or "chokepoint" in result.reason.lower()


def test_explanation_has_required_fields(red_sea_event):
    """Rule provides explanation step with timestamp."""
    rule = GeographicRelevanceRule()
    app_result = rule.apply(red_sea_event)
    step = rule.explain(red_sea_event, app_result)
    assert step.rule_name == "geographic_relevance"
    assert step.rule_version == "2.0.0"
    assert "keyword_count" in step.input_summary or "location_count" in step.input_summary
    assert step.output_summary.get("status") == app_result.status.value
    assert step.reasoning == app_result.reason
    assert step.timestamp is not None


def test_deterministic_output(red_sea_event):
    """Same input produces same result."""
    rule = GeographicRelevanceRule()
    r1 = rule.apply(red_sea_event)
    r2 = rule.apply(red_sea_event)
    assert r1.status == r2.status
    assert r1.score == r2.score
    assert r1.reason == r2.reason


def test_haversine_distance():
    """Internal haversine returns reasonable distance for known points."""
    rule = GeographicRelevanceRule()
    # Red Sea and Suez Canal are ~1200 km apart
    red_sea = CHOKEPOINTS["Red Sea"]
    suez = CHOKEPOINTS["Suez Canal"]
    d = rule._haversine_distance(red_sea, suez)
    assert 800 < d < 1600
    assert rule._haversine_distance(red_sea, red_sea) == 0.0
