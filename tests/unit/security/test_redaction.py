"""Tests for field redaction (pure OmenSignal contract)."""

from datetime import datetime

import pytest

from omen.domain.models.omen_signal import (
    OmenSignal,
    ConfidenceLevel,
    SignalCategory,
    GeographicContext,
    TemporalContext,
)
from omen.infrastructure.security.redaction import (
    redact_for_webhook,
    redact_for_api,
    redact_signal_for_external,
    ALWAYS_REDACT,
)


@pytest.fixture
def minimal_signal() -> OmenSignal:
    """Minimal pure OmenSignal for redaction tests."""
    return OmenSignal(
        signal_id="OMEN-TEST123",
        source_event_id="e1",
        input_event_hash="abc123",
        title="Test signal",
        description="Short description",
        probability=0.5,
        probability_source="test",
        probability_is_estimate=False,
        confidence_score=0.8,
        confidence_level=ConfidenceLevel.HIGH,
        confidence_factors={"v": 0.8, "l": 0.7},
        category=SignalCategory.GEOPOLITICAL,
        tags=[],
        keywords_matched=[],
        geographic=GeographicContext(),
        temporal=TemporalContext(),
        evidence=[],
        validation_scores=[],
        trace_id="dt1",
        ruleset_version="v1",
        source_url=None,
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


def test_redact_for_webhook_pure_contract_fields(minimal_signal):
    """Webhook redaction includes pure contract fields."""
    out = redact_for_webhook(minimal_signal)
    assert "signal_id" in out
    assert "source_event_id" in out
    assert "probability" in out
    assert "confidence_level" in out
    assert "trace_id" in out


def test_redact_for_api_minimal(minimal_signal):
    """redact_for_api minimal returns pure-contract subset."""
    out = redact_for_api(minimal_signal, detail_level="minimal")
    assert "signal_id" in out
    assert "source_event_id" in out
    assert "title" in out
    assert "probability" in out
    assert "confidence_level" in out
    assert "trace_id" in out
    assert "generated_at" in out


def test_redact_for_api_standard(minimal_signal):
    """redact_for_api standard returns redacted full structure."""
    out = redact_for_api(minimal_signal, detail_level="standard")
    assert isinstance(out, dict)
    assert out.get("signal_id") == "OMEN-TEST123"


def test_redact_signal_for_external_full_detail(minimal_signal):
    """With include_confidence_breakdown, keeps factors; excludes internal fields."""
    out = redact_signal_for_external(
        minimal_signal,
        include_explanation=False,
        include_confidence_breakdown=True,
    )
    assert "trace_id" in out
    assert "_source_assessment" not in out
