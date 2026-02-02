"""
CRITICAL TESTS: Verify OMEN is Signal Engine, NOT Decision Engine.

These tests ensure OMEN follows its core principle:
- Emit signals with metrics, evidence, and confidence
- NEVER emit risk verdicts or make decisions

If any of these tests fail, it indicates a CRITICAL violation
of OMEN's architectural contract.
"""

import pytest
from datetime import datetime, timezone
from typing import Any

from omen.adapters.inbound.partner_risk.models import (
    PartnerSignalMetrics,
    PartnerSignalConfidence,
    PartnerSignalEvidence,
    PartnerSignalResponse,
    PartnerSignalsListResponse,
)


class TestSignalEngineCompliance:
    """Tests that verify OMEN doesn't make risk decisions."""
    
    # Fields that MUST NOT exist in any API response
    FORBIDDEN_FIELDS = {
        "risk_status",
        "overall_risk",
        "risk_breakdown",
        "risk_level",
        "risk_score",
        "risk_verdict",
        "recommendation",
        "decision",
        "action_required",
        "alert_level",
    }
    
    # Fields that MUST exist (signal metrics)
    REQUIRED_SIGNAL_FIELDS = {
        "price_change_percent",
    }
    
    def _check_no_forbidden_fields(self, obj: Any, path: str = "root") -> None:
        """
        Recursively check that no forbidden fields exist in object.
        
        Raises AssertionError if any forbidden field is found.
        """
        if isinstance(obj, dict):
            for key, value in obj.items():
                assert key not in self.FORBIDDEN_FIELDS, (
                    f"CRITICAL VIOLATION: Found forbidden field '{key}' at {path}. "
                    f"OMEN must NOT emit risk verdicts!"
                )
                self._check_no_forbidden_fields(value, f"{path}.{key}")
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                self._check_no_forbidden_fields(item, f"{path}[{i}]")
    
    def test_partner_signal_response_has_no_risk_verdict(self):
        """PartnerSignalResponse must NOT contain risk verdicts."""
        now = datetime.now(timezone.utc)
        
        response = PartnerSignalResponse(
            symbol="HAH",
            company_name="Hai An Transport",
            exchange="HOSE",
            signals=PartnerSignalMetrics(
                price_current=32.5,
                price_change_percent=-2.1,
            ),
            confidence=PartnerSignalConfidence(
                overall_confidence=0.85,
                data_completeness=0.9,
                data_freshness_seconds=120,
                data_source="vnstock",
                data_source_reliability=0.95,
            ),
            signal_id="test-signal-001",
            timestamp=now,
        )
        
        # Convert to dict and check
        data = response.model_dump()
        self._check_no_forbidden_fields(data)
    
    def test_partner_signals_list_response_has_no_risk_verdict(self):
        """PartnerSignalsListResponse must NOT contain risk verdicts."""
        now = datetime.now(timezone.utc)
        
        partner = PartnerSignalResponse(
            symbol="HAH",
            company_name="Hai An Transport",
            exchange="HOSE",
            signals=PartnerSignalMetrics(
                price_current=32.5,
                price_change_percent=-2.1,
            ),
            confidence=PartnerSignalConfidence(
                overall_confidence=0.85,
                data_completeness=0.9,
                data_freshness_seconds=120,
                data_source="vnstock",
                data_source_reliability=0.95,
            ),
            signal_id="test-signal-001",
            timestamp=now,
        )
        
        response = PartnerSignalsListResponse(
            timestamp=now,
            total_partners=1,
            partners=[partner],
        )
        
        # Convert to dict and check
        data = response.model_dump()
        self._check_no_forbidden_fields(data)
    
    def test_response_has_signals(self):
        """PartnerSignalResponse must contain signal metrics."""
        now = datetime.now(timezone.utc)
        
        response = PartnerSignalResponse(
            symbol="HAH",
            company_name="Hai An Transport",
            exchange="HOSE",
            signals=PartnerSignalMetrics(
                price_current=32.5,
                price_change_percent=-2.1,
                volume=150000,
                trend_1d=-2.1,
            ),
            confidence=PartnerSignalConfidence(
                overall_confidence=0.85,
                data_completeness=0.9,
                data_freshness_seconds=120,
                data_source="vnstock",
                data_source_reliability=0.95,
            ),
            signal_id="test-signal-001",
            timestamp=now,
        )
        
        assert response.signals is not None
        assert response.signals.price_current is not None
        assert response.signals.price_change_percent is not None
    
    def test_response_has_confidence(self):
        """PartnerSignalResponse must contain confidence metrics."""
        now = datetime.now(timezone.utc)
        
        response = PartnerSignalResponse(
            symbol="HAH",
            company_name="Hai An Transport",
            exchange="HOSE",
            signals=PartnerSignalMetrics(
                price_current=32.5,
                price_change_percent=-2.1,
            ),
            confidence=PartnerSignalConfidence(
                overall_confidence=0.85,
                data_completeness=0.9,
                data_freshness_seconds=120,
                data_source="vnstock",
                data_source_reliability=0.95,
            ),
            signal_id="test-signal-001",
            timestamp=now,
        )
        
        assert response.confidence is not None
        assert 0 <= response.confidence.overall_confidence <= 1
        assert 0 <= response.confidence.data_completeness <= 1
    
    def test_response_can_have_evidence(self):
        """PartnerSignalResponse can contain evidence trail."""
        now = datetime.now(timezone.utc)
        
        evidence = PartnerSignalEvidence(
            evidence_id="ev-001",
            evidence_type="PRICE_CHANGE",
            title="HAH price decreased 2.1%",
            raw_value=-2.1,
            normalized_value=0.21,
            source="vnstock",
            observed_at=now,
        )
        
        response = PartnerSignalResponse(
            symbol="HAH",
            company_name="Hai An Transport",
            exchange="HOSE",
            signals=PartnerSignalMetrics(
                price_current=32.5,
                price_change_percent=-2.1,
            ),
            confidence=PartnerSignalConfidence(
                overall_confidence=0.85,
                data_completeness=0.9,
                data_freshness_seconds=120,
                data_source="vnstock",
                data_source_reliability=0.95,
            ),
            evidence=[evidence],
            signal_id="test-signal-001",
            timestamp=now,
        )
        
        assert response.evidence is not None
        assert len(response.evidence) == 1
        assert response.evidence[0].evidence_type == "PRICE_CHANGE"
    
    def test_suggestion_has_disclaimer(self):
        """If omen_suggestion exists, must have disclaimer."""
        now = datetime.now(timezone.utc)
        
        response = PartnerSignalResponse(
            symbol="HAH",
            company_name="Hai An Transport",
            exchange="HOSE",
            signals=PartnerSignalMetrics(
                price_current=32.5,
                price_change_percent=-2.1,
            ),
            confidence=PartnerSignalConfidence(
                overall_confidence=0.85,
                data_completeness=0.9,
                data_freshness_seconds=120,
                data_source="vnstock",
                data_source_reliability=0.95,
            ),
            omen_suggestion="Consider monitoring closely",
            signal_id="test-signal-001",
            timestamp=now,
        )
        
        # If suggestion exists, disclaimer must also exist
        if response.omen_suggestion:
            assert response.suggestion_disclaimer is not None
            assert len(response.suggestion_disclaimer) > 0
            # Disclaimer must mention RiskCast responsibility
            assert "RiskCast" in response.suggestion_disclaimer
    
    def test_aggregated_metrics_no_risk_verdict(self):
        """Aggregated metrics must NOT contain risk verdicts."""
        now = datetime.now(timezone.utc)
        
        partner = PartnerSignalResponse(
            symbol="HAH",
            company_name="Hai An Transport",
            exchange="HOSE",
            signals=PartnerSignalMetrics(
                price_current=32.5,
                price_change_percent=-2.1,
            ),
            confidence=PartnerSignalConfidence(
                overall_confidence=0.85,
                data_completeness=0.9,
                data_freshness_seconds=120,
                data_source="vnstock",
                data_source_reliability=0.95,
            ),
            signal_id="test-signal-001",
            timestamp=now,
        )
        
        response = PartnerSignalsListResponse(
            timestamp=now,
            total_partners=1,
            partners=[partner],
            aggregated_metrics={
                "avg_confidence": 0.85,
                "avg_price_change": -2.1,
                "total_signals": 1,
            },
        )
        
        # Check aggregated metrics
        for key in response.aggregated_metrics.keys():
            assert key not in self.FORBIDDEN_FIELDS, (
                f"Forbidden field '{key}' in aggregated_metrics"
            )
    
    def test_signal_metrics_are_immutable(self):
        """Signal metrics should be immutable (frozen=True)."""
        metrics = PartnerSignalMetrics(
            price_current=32.5,
            price_change_percent=-2.1,
        )
        
        # Attempting to modify should raise
        with pytest.raises(Exception):  # ValidationError or AttributeError
            metrics.price_current = 35.0
    
    def test_confidence_is_bounded(self):
        """Confidence values must be between 0 and 1."""
        # Note: datetime not needed for this test
        
        # Should work with valid values
        confidence = PartnerSignalConfidence(
            overall_confidence=0.5,
            data_completeness=0.8,
            data_freshness_seconds=60,
            data_source="test",
            data_source_reliability=0.9,
        )
        assert 0 <= confidence.overall_confidence <= 1
        
        # Should fail with invalid values
        with pytest.raises(Exception):  # ValidationError
            PartnerSignalConfidence(
                overall_confidence=1.5,  # Invalid: > 1
                data_completeness=0.8,
                data_freshness_seconds=60,
                data_source="test",
                data_source_reliability=0.9,
            )
    
    def test_evidence_has_source_and_timestamp(self):
        """Each evidence item must have source and timestamp."""
        now = datetime.now(timezone.utc)
        
        evidence = PartnerSignalEvidence(
            evidence_id="ev-001",
            evidence_type="PRICE_CHANGE",
            title="Price changed",
            raw_value=-2.1,
            normalized_value=0.21,
            source="vnstock",
            observed_at=now,
        )
        
        assert evidence.source is not None
        assert len(evidence.source) > 0
        assert evidence.observed_at is not None


class TestSignalEngineAPIContract:
    """Tests for API contract compliance."""
    
    def test_response_schema_version(self):
        """Response must include schema version."""
        now = datetime.now(timezone.utc)
        
        response = PartnerSignalResponse(
            symbol="HAH",
            company_name="Hai An Transport",
            exchange="HOSE",
            signals=PartnerSignalMetrics(
                price_current=32.5,
                price_change_percent=-2.1,
            ),
            confidence=PartnerSignalConfidence(
                overall_confidence=0.85,
                data_completeness=0.9,
                data_freshness_seconds=120,
                data_source="vnstock",
                data_source_reliability=0.95,
            ),
            signal_id="test-signal-001",
            timestamp=now,
        )
        
        assert response.schema_version is not None
        assert response.schema_version == "2.0.0"
    
    def test_response_omen_version(self):
        """Response must include OMEN version."""
        now = datetime.now(timezone.utc)
        
        response = PartnerSignalResponse(
            symbol="HAH",
            company_name="Hai An Transport",
            exchange="HOSE",
            signals=PartnerSignalMetrics(
                price_current=32.5,
                price_change_percent=-2.1,
            ),
            confidence=PartnerSignalConfidence(
                overall_confidence=0.85,
                data_completeness=0.9,
                data_freshness_seconds=120,
                data_source="vnstock",
                data_source_reliability=0.95,
            ),
            signal_id="test-signal-001",
            timestamp=now,
        )
        
        assert response.omen_version is not None
        assert response.omen_version.startswith("2.")
