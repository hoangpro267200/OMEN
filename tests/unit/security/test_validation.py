"""Tests for input validation and sanitization."""

import pytest

from omen.infrastructure.security.validation import (
    sanitize_string,
    sanitize_dict,
    SecureEventInput,
)


def test_sanitize_string_empty():
    """Empty string is returned as-is."""
    assert sanitize_string("") == ""
    assert sanitize_string(None or "") == ""


def test_sanitize_string_truncates():
    """Long string is truncated to max_length."""
    long = "a" * 20000
    out = sanitize_string(long, max_length=100)
    assert len(out) == 100


def test_sanitize_string_removes_null_bytes():
    """Null bytes are removed."""
    assert "\x00" not in sanitize_string("hello\x00world")


def test_sanitize_string_rejects_script():
    """Script tags raise ValueError."""
    with pytest.raises(ValueError, match="dangerous"):
        sanitize_string("<script>alert(1)</script>")


def test_sanitize_string_rejects_javascript_uri():
    """javascript: URI raises."""
    with pytest.raises(ValueError, match="dangerous"):
        sanitize_string("javascript:alert(1)")


def test_sanitize_dict_recursive():
    """Nested dicts are sanitized."""
    data = {"a": "safe", "b": {"c": "also"}}
    out = sanitize_dict(data)
    assert out == data


def test_sanitize_dict_max_depth():
    """Max depth is enforced."""
    deep = {"x": {"y": {"z": {"w": {"v": "too deep"}}}}}
    with pytest.raises(ValueError, match="nested too deeply"):
        sanitize_dict(deep, max_depth=3)


def test_secure_event_input_valid():
    """SecureEventInput accepts valid input."""
    inp = SecureEventInput(
        event_id="evt_123",
        title="Red Sea disruption",
        description="Some description",
        probability=0.5,
        source="polymarket",
    )
    assert inp.event_id == "evt_123"
    assert inp.source == "polymarket"


def test_secure_event_input_event_id_format():
    """event_id must be alphanumeric with - and _."""
    with pytest.raises(ValueError, match="event_id"):
        SecureEventInput(
            event_id="bad id!",
            title="T",
            probability=0.5,
            source="manual",
        )


def test_secure_event_input_probability_bounds():
    """probability must be in [0, 1]."""
    with pytest.raises(ValueError, match="probability"):
        SecureEventInput(
            event_id="e1",
            title="T",
            probability=1.5,
            source="manual",
        )


def test_secure_event_input_source_allowed():
    """source must be in allowed set."""
    with pytest.raises(ValueError, match="source"):
        SecureEventInput(
            event_id="e1",
            title="T",
            probability=0.5,
            source="unknown_source",
        )
