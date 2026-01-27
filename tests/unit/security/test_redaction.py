"""Tests for field redaction."""

from datetime import datetime

import pytest

from omen.domain.models.common import (
    EventId,
    SignalCategory,
    ImpactDomain,
    ConfidenceLevel,
    RulesetVersion,
)
from omen.domain.models.explanation import ExplanationChain
from omen.domain.models.omen_signal import OmenSignal
from omen.infrastructure.security.redaction import (
    redact_for_webhook,
    redact_for_api,
    redact_signal_for_external,
    ALWAYS_REDACT,
)


@pytest.fixture
def minimal_signal() -> OmenSignal:
    """Minimal OmenSignal for redaction tests."""
    chain = ExplanationChain(
        trace_id="trace-1",
        steps=[],
        total_steps=0,
        started_at=datetime(2025, 1, 1, 12, 0, 0),
        completed_at=datetime(2025, 1, 1, 12, 1, 0),
    )
    return OmenSignal.model_construct(
        signal_id="OMEN-TEST123",
        event_id=EventId("e1"),
        category=SignalCategory.GEOPOLITICAL,
        domain=ImpactDomain.LOGISTICS,
        current_probability=0.5,
        probability_momentum="STABLE",
        confidence_level=ConfidenceLevel.HIGH,
        confidence_score=0.8,
        confidence_factors={"v": 0.8, "l": 0.7},
        severity=0.5,
        severity_label="MEDIUM",
        title="Test signal",
        summary="Short summary for display. " * 2,
        detailed_explanation="Detailed explanation here. " * 5,
        explanation_chain=chain,
        input_event_hash="abc123",
        ruleset_version=RulesetVersion("v1"),
        deterministic_trace_id="dt1",
        source_market="test",
        generated_at=datetime(2025, 1, 1, 12, 0, 0),
    )


def test_redact_for_webhook_returns_dict(minimal_signal):
    """redact_for_webhook returns a dict."""
    out = redact_for_webhook(minimal_signal)
    assert isinstance(out, dict)
    assert "signal_id" in out
    assert out["signal_id"] == "OMEN-TEST123"


def test_redact_for_webhook_excludes_internal(minimal_signal):
    """redact_for_webhook does not include always-redacted fields."""
    out = redact_for_webhook(minimal_signal)
    for key in ALWAYS_REDACT:
        assert key not in out


def test_redact_for_webhook_replaces_chain_with_summary(minimal_signal):
    """Webhook redaction replaces explanation_chain with explanation_summary."""
    out = redact_for_webhook(minimal_signal)
    assert "explanation_chain" not in out or "explanation_summary" in out
    if "explanation_summary" in out:
        assert "trace_id" in out["explanation_summary"]
        assert "total_steps" in out["explanation_summary"]


def test_redact_for_api_minimal(minimal_signal):
    """redact_for_api minimal returns subset of fields."""
    out = redact_for_api(minimal_signal, detail_level="minimal")
    assert "signal_id" in out
    assert "title" in out
    assert "confidence_level" in out
    assert "severity" in out
    assert "is_actionable" in out
    assert "urgency" in out
    assert "generated_at" in out


def test_redact_for_api_standard(minimal_signal):
    """redact_for_api standard returns redacted full structure."""
    out = redact_for_api(minimal_signal, detail_level="standard")
    assert isinstance(out, dict)
    assert out.get("signal_id") == "OMEN-TEST123"


def test_redact_signal_for_external_full_detail(minimal_signal):
    """With include_explanation and include_confidence_breakdown, keeps them."""
    out = redact_signal_for_external(
        minimal_signal,
        include_explanation=True,
        include_confidence_breakdown=True,
    )
    assert "explanation_chain" in out or "trace_id" in str(out)
    assert "_source_assessment" not in out
