"""
Tests to verify no fake data in live API responses.

Phase 1: probability_history, confidence_breakdown, metric projection, delay_days
must come from pipeline or storage, never from hash/random/formula.
"""

import pytest
from unittest.mock import MagicMock, patch

from omen.infrastructure.storage.signal_history import SignalHistoryStore
from omen.api.routes.live import (
    _signal_to_full_response,
    _route_coords,
    _confidence_breakdown_from_factors,
    _enhance_metric,
)


@pytest.fixture
def fresh_history_store():
    """Return a new store with no data (isolated from global)."""
    return SignalHistoryStore()


@pytest.fixture
def minimal_signal():
    """Minimal OmenSignal-like object for _signal_to_full_response."""
    s = MagicMock()
    s.signal_id = "OMEN-TESTINTEG001"
    s.event_id = "polymarket-0xabc"
    s.title = "Test signal"
    s.current_probability = 0.75
    s.confidence_score = 0.8
    s.confidence_level = MagicMock(value="HIGH")
    s.severity = 0.7
    s.severity_label = "HIGH"
    s.key_metrics = []
    s.affected_routes = []
    s.affected_regions = []
    s.explanation_chain = MagicMock(steps=[])
    s.deterministic_trace_id = "trace-1"
    s.ruleset_version = None
    s.domain = None
    s.category = None
    s.subcategory = None
    s.summary = "Summary"
    s.detailed_explanation = "Explanation"
    s.expected_onset_hours = None
    s.expected_duration_hours = None
    s.source_market = "polymarket"
    s.market_url = None
    s.affected_systems = []
    s.generated_at = MagicMock()
    s.urgency = "HIGH"
    s.input_event_hash = "abc123"
    return s


class TestProbabilityHistoryIntegrity:
    """probability_history must come from storage or be empty."""

    @patch("omen.api.routes.live.get_signal_history_store")
    def test_probability_history_empty_when_no_history(
        self, mock_get_store, fresh_history_store, minimal_signal
    ):
        mock_get_store.return_value = fresh_history_store
        resp = _signal_to_full_response(minimal_signal)
        assert resp.probability_history == []
        assert resp.probability_momentum in ("UNKNOWN", "STABLE")

    @patch("omen.api.routes.live.get_signal_history_store")
    def test_probability_history_from_real_records(
        self, mock_get_store, fresh_history_store, minimal_signal
    ):
        mock_get_store.return_value = fresh_history_store
        sid = minimal_signal.signal_id
        for i in range(4):
            fresh_history_store.record(sid, 0.70 + i * 0.02, "polymarket_gamma", "mkt-1")
        resp = _signal_to_full_response(minimal_signal)
        assert len(resp.probability_history) == 4
        assert resp.probability_history[0] == pytest.approx(0.70)
        assert resp.probability_history[-1] == pytest.approx(0.76)


class TestConfidenceBreakdownIntegrity:
    """confidence_breakdown must come from pipeline factors, not hash."""

    def test_confidence_breakdown_from_factors(self):
        score = 0.8
        factors = {"liquidity_score": 0.9, "geographic_score": 0.85, "source_reliability_score": 0.85}
        cb = _confidence_breakdown_from_factors(score, factors)
        assert cb.liquidity == 0.9
        assert cb.geographic == 0.85
        assert cb.source_reliability == 0.85

    def test_confidence_breakdown_fallback_no_hash(self):
        """When factors are missing, all components use overall score — no hash(signal_id)."""
        cb1 = _confidence_breakdown_from_factors(0.7, None)
        cb2 = _confidence_breakdown_from_factors(0.7, {})
        for cb in (cb1, cb2):
            assert cb.liquidity == 0.7
            assert cb.geographic == 0.7
            assert cb.semantic == 0.7
            assert cb.anomaly == 0.7
            assert cb.market_depth == 0.7
            assert cb.source_reliability == 0.7


class TestMetricProjectionIntegrity:
    """Metric projection must be empty (no unsourced formula)."""

    def test_enhance_metric_no_projection(self):
        m = MagicMock()
        m.name = "transit_time_increase"
        m.value = 7.5
        m.unit = "days"
        m.uncertainty = None
        m.baseline = 0
        m.evidence_source = "Drewry 2024"
        em = _enhance_metric(m)
        assert em.projection == []


class TestDelayDaysIntegrity:
    """delay_days must come from AffectedRoute.estimated_delay_days, not severity * 10."""

    def test_route_coords_uses_provided_delay_days(self):
        r = _route_coords("East Asia", "Northern Europe", 0.75, delay_days=7.5)
        assert r.delay_days == 7.5

    def test_route_coords_zero_when_delay_not_provided(self):
        r = _route_coords("East Asia", "Northern Europe", 0.75)
        assert r.delay_days == 0.0

    @patch("omen.api.routes.live.get_signal_history_store")
    def test_full_response_route_delay_from_assessment(
        self, mock_get_store, fresh_history_store, minimal_signal
    ):
        mock_get_store.return_value = fresh_history_store
        route = MagicMock()
        route.origin_region = "East Asia"
        route.destination_region = "Northern Europe"
        route.impact_severity = 0.75
        route.estimated_delay_days = 8.2
        minimal_signal.affected_routes = [route]
        resp = _signal_to_full_response(minimal_signal)
        assert len(resp.affected_routes) == 1
        assert resp.affected_routes[0].delay_days == 8.2
