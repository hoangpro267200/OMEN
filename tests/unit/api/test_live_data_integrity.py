"""
Tests to verify live API returns signal-only contract (no impact-shaped data).

Phase 1: Responses must be SignalResponse only — no impact_severity, delay_days,
metrics, affected_routes, or other impact-assessment fields in the API layer.
"""

import pytest

from omen.api.models.responses import SignalResponse
from omen.api.routes.live import router


@pytest.fixture
def minimal_signal():
    """Minimal OmenSignal-like object for SignalResponse.from_domain (pure contract)."""
    from datetime import datetime
    from omen.domain.models.omen_signal import (
        OmenSignal,
        ConfidenceLevel,
        SignalCategory,
        GeographicContext,
        TemporalContext,
        EvidenceItem,
    )
    return OmenSignal(
        signal_id="OMEN-TESTINTEG001",
        source_event_id="polymarket-0xabc",
        title="Test signal",
        description="Summary",
        probability=0.75,
        probability_source="polymarket",
        probability_is_estimate=False,
        confidence_score=0.8,
        confidence_level=ConfidenceLevel.HIGH,
        confidence_factors={"liquidity": 0.9, "geographic": 0.85},
        category=SignalCategory.GEOPOLITICAL,
        tags=[],
        keywords_matched=[],
        geographic=GeographicContext(regions=[], chokepoints=[]),
        temporal=TemporalContext(event_horizon=None, resolution_date=None),
        evidence=[
            EvidenceItem(source="Polymarket", source_type="market", url=None),
        ],
        validation_scores=[],
        trace_id="trace-1",
        ruleset_version="1.0.0",
        source_url=None,
        generated_at=datetime(2025, 1, 1, 12, 0, 0),
    )


class TestLiveSignalOnlyContract:
    """Live API must return signal-shaped data only; no impact fields."""

    def test_signal_response_has_no_impact_fields(self, minimal_signal):
        """SignalResponse.from_domain produces no impact_severity, delay_days, etc."""
        resp = SignalResponse.from_domain(minimal_signal)
        data = resp.model_dump()
        assert "impact_severity" not in data
        assert "delay_days" not in data
        assert "urgency" not in data
        assert "is_actionable" not in data
        assert "risk_exposure" not in data
        assert "recommended_action" not in data
        assert "affected_routes" not in data
        assert "metrics" not in data

    def test_signal_response_has_required_signal_fields(self, minimal_signal):
        """SignalResponse contains probability, confidence, context, trace_id."""
        resp = SignalResponse.from_domain(minimal_signal)
        assert resp.signal_id == "OMEN-TESTINTEG001"
        assert resp.probability == 0.75
        assert resp.confidence_score == 0.8
        assert resp.confidence_level == "HIGH"
        assert resp.trace_id == "trace-1"
        assert resp.probability_source == "polymarket"
        assert resp.geographic is not None
        assert resp.temporal is not None
        assert resp.evidence is not None

    def test_live_router_exists(self):
        """Live router is registered with expected prefix."""
        assert router.prefix == "/live"
        assert router.tags == ["Live Data"]
