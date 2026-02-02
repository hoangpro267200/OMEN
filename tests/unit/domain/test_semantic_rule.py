"""Tests for SemanticRelevanceRule."""

import pytest

from omen.domain.models.common import EventId, MarketId, ValidationStatus
from omen.domain.models.raw_signal import RawSignalEvent, MarketMetadata
from omen.domain.rules.validation.semantic_relevance_rule import (
    SemanticRelevanceRule,
    RISK_CATEGORIES,
    MIN_RELEVANCE_SCORE,
)


@pytest.fixture
def logistics_risk_event() -> RawSignalEvent:
    """Event with conflict and infrastructure keywords."""
    return RawSignalEvent(
        event_id=EventId("sem-1"),
        title="Port closure and strike at major terminal",
        description="Union walkout and blockade at shipping hub",
        probability=0.5,
        keywords=["strike", "port", "closure", "blockade", "shipping"],
        market=MarketMetadata(
            source="t",
            market_id=MarketId("m1"),
            total_volume_usd=10000.0,
            current_liquidity_usd=5000.0,
        ),
    )


@pytest.fixture
def irrelevant_semantic_event() -> RawSignalEvent:
    """Event with no risk keywords. Avoid substrings (e.g. 'port' in 'sports')."""
    return RawSignalEvent(
        event_id=EventId("sem-irr-1"),
        title="Which team wins the match?",
        description="Outcome of the game.",
        probability=0.3,
        keywords=["football", "final", "cup"],
        market=MarketMetadata(
            source="t",
            market_id=MarketId("m2"),
            total_volume_usd=10000.0,
            current_liquidity_usd=5000.0,
        ),
    )


def test_passes_when_risk_keywords_present(logistics_risk_event):
    """Rule passes when logistics risk categories are detected."""
    rule = SemanticRelevanceRule()
    result = rule.apply(logistics_risk_event)
    assert result.status == ValidationStatus.PASSED
    assert result.score >= MIN_RELEVANCE_SCORE
    assert "risk categories" in result.reason.lower() or "relevant" in result.reason.lower()


def test_rejects_when_no_risk_keywords(irrelevant_semantic_event):
    """Rule rejects when no logistics risk keywords."""
    rule = SemanticRelevanceRule()
    result = rule.apply(irrelevant_semantic_event)
    assert result.status == ValidationStatus.REJECTED_IRRELEVANT_SEMANTIC
    assert "No logistics risk keywords" in result.reason or "detected" in result.reason


def test_rejects_when_no_matching_categories():
    """Rule rejects when text has no risk-category keywords."""
    rule = SemanticRelevanceRule()
    event = RawSignalEvent(
        event_id=EventId("sem-weak"),
        title="Maybe something",
        description="vessel cargo",
        probability=0.5,
        keywords=[],
        market=MarketMetadata(
            source="t",
            market_id=MarketId("m1"),
            total_volume_usd=10000.0,
            current_liquidity_usd=5000.0,
        ),
    )
    # "vessel" and "cargo" are not in RISK_CATEGORIES
    result = rule.apply(event)
    assert result.status == ValidationStatus.REJECTED_IRRELEVANT_SEMANTIC


def test_explanation_has_required_fields(logistics_risk_event):
    """Rule provides explanation step."""
    rule = SemanticRelevanceRule()
    app_result = rule.apply(logistics_risk_event)
    step = rule.explain(logistics_risk_event, app_result)
    assert step.rule_name == "semantic_relevance"
    assert step.rule_version == "2.0.0"
    assert step.output_summary.get("status") == app_result.status.value
    assert step.reasoning == app_result.reason
    assert step.timestamp is not None


def test_deterministic_output(logistics_risk_event):
    """Same input produces same result."""
    rule = SemanticRelevanceRule()
    r1 = rule.apply(logistics_risk_event)
    r2 = rule.apply(logistics_risk_event)
    assert r1.status == r2.status
    assert r1.score == r2.score
    assert r1.reason == r2.reason


def test_multiple_categories_increase_score():
    """More risk categories increase score."""
    rule = SemanticRelevanceRule()
    single = RawSignalEvent(
        event_id=EventId("s1"),
        title="port closure",
        probability=0.5,
        keywords=[],
        market=MarketMetadata(
            source="t",
            market_id=MarketId("m1"),
            total_volume_usd=10000.0,
            current_liquidity_usd=5000.0,
        ),
    )
    multi = RawSignalEvent(
        event_id=EventId("s2"),
        title="port closure strike war attack blockade sanction",
        description="conflict and labor and sanctions",
        probability=0.5,
        keywords=[],
        market=MarketMetadata(
            source="t",
            market_id=MarketId("m2"),
            total_volume_usd=10000.0,
            current_liquidity_usd=5000.0,
        ),
    )
    r_single = rule.apply(single)
    r_multi = rule.apply(multi)
    assert r_multi.score >= r_single.score
