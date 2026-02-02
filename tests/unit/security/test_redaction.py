"""Tests for field redaction (pure OmenSignal contract) and secret redaction in logs."""

import logging
from datetime import datetime
from io import StringIO

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
    redact_secrets,
    redact_dict,
    RedactingFormatter,
    RedactingWrapperFormatter,
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


# ─── Secret redaction (logs) ─────────────────────────────────────────────────


def test_redact_secrets_redacts_api_key_like():
    """redact_secrets redacts api_key=value and similar patterns."""
    text = "Request api_key=sk_live_abc123xyz"
    out = redact_secrets(text)
    assert "sk_live_abc123xyz" not in out
    assert "[REDACTED]" in out
    assert "api_key=" in out


def test_redact_secrets_redacts_omen_key():
    """redact_secrets redacts omen_ prefixed long keys (standalone or in header)."""
    text = "Authorization: omen_AbCdEfGhIjKlMnOpQrStUvWxYz123456"
    out = redact_secrets(text)
    assert "omen_AbCdEfGhIjKlMnOpQrStUvWxYz123456" not in out
    assert "[REDACTED]" in out or "[REDACTED_KEY]" in out
    # Standalone omen_ key is replaced with [REDACTED_KEY]
    out2 = redact_secrets("key=omen_AbCdEfGhIjKlMnOpQrStUvWxYz123456")
    assert "omen_AbCdEfGhIjKlMnOpQrStUvWxYz123456" not in out2
    assert "[REDACTED_KEY]" in out2


def test_redact_secrets_redacts_bearer():
    """redact_secrets redacts Bearer token."""
    text = "Bearer eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ1c2VyIn0.x"
    out = redact_secrets(text)
    assert "eyJhbGciOiJIUzI1NiJ9" not in out
    assert "Bearer " in out
    assert "[REDACTED]" in out


def test_redact_dict_redacts_sensitive_keys():
    """redact_dict replaces sensitive key values with [REDACTED]."""
    data = {"user": "alice", "api_key": "secret123", "role": "admin"}
    out = redact_dict(data)
    assert out["user"] == "alice"
    assert out["api_key"] == "[REDACTED]"
    assert out["role"] == "admin"


def test_log_output_does_not_contain_plaintext_api_key():
    """Log output must not contain plaintext API keys (acceptance: grep returns 0)."""
    plaintext_key = "omen_TestKey32CharsLongExactly!!!!!!!!"
    log_capture = StringIO()
    handler = logging.StreamHandler(log_capture)
    handler.setFormatter(RedactingWrapperFormatter(logging.Formatter("%(message)s")))
    logger = logging.getLogger("test.redaction")
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    try:
        logger.info("Request with api_key=%s", plaintext_key)
        logger.info("Header: Authorization: Bearer %s", plaintext_key)
        output = log_capture.getvalue()
        assert plaintext_key not in output, "Log output must not contain plaintext API key"
        assert "[REDACTED]" in output or "[REDACTED_KEY]" in output
    finally:
        logger.removeHandler(handler)
