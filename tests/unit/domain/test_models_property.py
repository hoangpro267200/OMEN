"""
Property-based tests using Hypothesis.

These tests verify model invariants hold for arbitrary valid inputs.
"""

import pytest
from hypothesis import given, strategies as st

from omen.domain.models.common import (
    EventId,
    MarketId,
    ConfidenceLevel,
)
from omen.domain.models.raw_signal import RawSignalEvent, MarketMetadata


def create_event(
    *,
    probability: float = 0.5,
    liquidity: float = 50_000.0,
    event_id: str = "prop-test-001",
    title: str = "Property test event",
) -> RawSignalEvent:
    """Build a minimal valid RawSignalEvent for property tests."""
    return RawSignalEvent(
        event_id=EventId(event_id),
        title=title,
        probability=probability,
        market=MarketMetadata(
            source="hypothesis",
            market_id=MarketId("prop-market"),
            total_volume_usd=max(0, liquidity * 2),
            current_liquidity_usd=max(0, liquidity),
        ),
    )


class TestRawSignalEventProperties:
    """Invariants for RawSignalEvent."""

    @given(
        probability=st.floats(min_value=0, max_value=1),
        liquidity=st.floats(min_value=0, max_value=1_000_000),
    )
    def test_input_event_hash_is_always_16_chars(self, probability, liquidity):
        """Hash length is always 16 characters."""
        event = create_event(probability=probability, liquidity=liquidity)
        assert len(event.input_event_hash) == 16

    @given(probability=st.floats(min_value=0, max_value=1))
    def test_probability_is_bounded(self, probability):
        """Probability must be in [0, 1]."""
        event = create_event(probability=probability)
        assert 0 <= event.probability <= 1


class TestConfidenceLevelProperties:
    """Invariants for ConfidenceLevel.from_score."""

    @given(score=st.floats(min_value=0, max_value=1))
    def test_from_score_always_returns_valid_level(self, score):
        """from_score never raises for valid scores."""
        level = ConfidenceLevel.from_score(score)
        assert level in [ConfidenceLevel.LOW, ConfidenceLevel.MEDIUM, ConfidenceLevel.HIGH]

    @given(score=st.floats(min_value=0.7, max_value=1.0))
    def test_high_scores_are_high_confidence(self, score):
        """Scores >= 0.7 must be HIGH."""
        assert ConfidenceLevel.from_score(score) == ConfidenceLevel.HIGH
