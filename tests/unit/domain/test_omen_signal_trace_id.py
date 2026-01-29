"""Tests for OmenSignal trace_id determinism (D7 Auditability)."""

from datetime import datetime
from unittest.mock import MagicMock

import pytest

from omen.domain.models.common import RulesetVersion, SignalCategory
from omen.domain.models.raw_signal import RawSignalEvent, MarketMetadata
from omen.domain.models.validated_signal import ValidatedSignal, ValidationResult
from omen.domain.models.common import EventId, MarketId, ValidationStatus
from omen.domain.models.omen_signal import OmenSignal, _generate_deterministic_trace_id


@pytest.fixture
def raw_event_a() -> RawSignalEvent:
    """Raw event with known identity for trace_id hashing."""
    return RawSignalEvent(
        event_id=EventId("test-event-123"),
        title="Test event",
        description="Desc",
        probability=0.6,
        market=MarketMetadata(
            source="test",
            market_id=MarketId("m1"),
            total_volume_usd=1000.0,
            current_liquidity_usd=500.0,
        ),
    )


@pytest.fixture
def raw_event_b() -> RawSignalEvent:
    """Different raw event (different event_id / hash)."""
    return RawSignalEvent(
        event_id=EventId("test-event-456"),
        title="Other event",
        probability=0.5,
        market=MarketMetadata(
            source="test",
            market_id=MarketId("m2"),
            total_volume_usd=2000.0,
            current_liquidity_usd=1000.0,
        ),
    )


@pytest.fixture
def minimal_enrichment():
    """Minimal enrichment dict for from_validated_event."""
    return {
        "matched_regions": [],
        "matched_chokepoints": ["red_sea"],
        "confidence_factors": {"liquidity": 0.9, "geographic": 0.8},
        "keyword_categories": {},
        "matched_keywords": ["red sea"],
        "validation_results": [
            ValidationResult(
                rule_name="liquidity_validation",
                rule_version="1.0.0",
                status=ValidationStatus.PASSED,
                score=0.9,
                reason="OK",
            )
        ],
    }


def test_generate_deterministic_trace_id_same_input_same_output():
    """_generate_deterministic_trace_id: same inputs -> same trace_id."""
    t1 = _generate_deterministic_trace_id("e1", "hash1", "1.0.0")
    t2 = _generate_deterministic_trace_id("e1", "hash1", "1.0.0")
    assert t1 == t2
    assert len(t1) == 16
    assert all(c in "0123456789abcdef" for c in t1)


def test_generate_deterministic_trace_id_different_input_different_output():
    """_generate_deterministic_trace_id: different inputs -> different trace_id."""
    t1 = _generate_deterministic_trace_id("e1", "hash1", "1.0.0")
    t2 = _generate_deterministic_trace_id("e2", "hash1", "1.0.0")
    t3 = _generate_deterministic_trace_id("e1", "hash2", "1.0.0")
    t4 = _generate_deterministic_trace_id("e1", "hash1", "2.0.0")
    assert t1 != t2 != t3 != t4


def test_generate_deterministic_trace_id_no_timestamp_pattern():
    """trace_id must not contain timestamp pattern (e.g. YYYYMMDD)."""
    t = _generate_deterministic_trace_id("e1", "h1", "1.0.0")
    assert "-202" not in t
    assert "2025" not in t


def test_trace_id_is_deterministic_when_fallback_used(
    raw_event_a, minimal_enrichment
):
    """Same input must produce same trace_id when using deterministic fallback."""
    ruleset = "2.0.0"
    mock_v = MagicMock()
    mock_v.original_event = raw_event_a
    mock_v.ruleset_version = ruleset
    mock_v.deterministic_trace_id = None  # force fallback
    mock_v.affected_chokepoints = []
    mock_v.validation_results = minimal_enrichment["validation_results"]
    mock_v.liquidity_score = 0.9
    mock_v.category = SignalCategory.GEOPOLITICAL
    mock_v.validated_at = datetime(2025, 1, 1, 12, 0, 0)

    signal1 = OmenSignal.from_validated_event(mock_v, minimal_enrichment)
    signal2 = OmenSignal.from_validated_event(mock_v, minimal_enrichment)
    assert signal1.trace_id == signal2.trace_id
    assert len(signal1.trace_id) == 16


def test_trace_id_changes_with_input(
    raw_event_a, raw_event_b, minimal_enrichment
):
    """Different event (different event_id/hash) must produce different trace_id."""
    ruleset = "1.0.0"
    def make_mock(event):
        m = MagicMock()
        m.original_event = event
        m.ruleset_version = ruleset
        m.deterministic_trace_id = None
        m.affected_chokepoints = []
        m.validation_results = minimal_enrichment["validation_results"]
        m.liquidity_score = 0.9
        m.category = SignalCategory.GEOPOLITICAL
        m.validated_at = datetime(2025, 1, 1, 12, 0, 0)
        return m

    signal1 = OmenSignal.from_validated_event(
        make_mock(raw_event_a), minimal_enrichment
    )
    signal2 = OmenSignal.from_validated_event(
        make_mock(raw_event_b), minimal_enrichment
    )
    assert signal1.trace_id != signal2.trace_id


def test_trace_id_uses_validated_if_present(
    validated_red_sea_signal, minimal_enrichment
):
    """If validated_signal has deterministic_trace_id, use it."""
    expected = validated_red_sea_signal.deterministic_trace_id
    signal = OmenSignal.from_validated_event(
        validated_red_sea_signal, minimal_enrichment
    )
    assert signal.trace_id == expected


def test_signal_id_derived_from_trace_id(raw_event_a, minimal_enrichment):
    """signal_id should be OMEN- + first 12 chars of trace_id (uppercase)."""
    mock_v = MagicMock()
    mock_v.original_event = raw_event_a
    mock_v.ruleset_version = "1.0.0"
    mock_v.deterministic_trace_id = None
    mock_v.affected_chokepoints = []
    mock_v.validation_results = minimal_enrichment["validation_results"]
    mock_v.liquidity_score = 0.9
    mock_v.category = SignalCategory.GEOPOLITICAL
    mock_v.validated_at = datetime(2025, 1, 1, 12, 0, 0)

    signal = OmenSignal.from_validated_event(mock_v, minimal_enrichment)
    assert signal.signal_id.startswith("OMEN-")
    assert len(signal.signal_id) == 5 + 12  # "OMEN-" + 12 chars
    assert signal.signal_id[5:].isupper() or signal.signal_id[5:].isdigit()
