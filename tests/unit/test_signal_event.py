"""Unit tests for SignalEvent envelope and LedgerRecord."""

from datetime import datetime, timezone

import pytest  # pyright: ignore[reportMissingImports]

from omen.domain.models.omen_signal import (
    OmenSignal,
    ConfidenceLevel,
    SignalCategory,
    GeographicContext,
    TemporalContext,
    ImpactHints,
)
from omen.domain.models.signal_event import (
    SignalEvent,
    LedgerRecord,
    SCHEMA_VERSION,
    generate_input_event_hash,
)
from omen.domain.models.enums import SignalType, SignalStatus


def _make_minimal_signal() -> OmenSignal:
    """Build a minimal valid OmenSignal for tests."""
    return OmenSignal(
        signal_id="OMEN-TEST123",
        source_event_id="test-event",
        trace_id="trace123abc",
        title="Test Signal",
        probability=0.5,
        probability_source="test",
        confidence_score=0.7,
        confidence_level=ConfidenceLevel.MEDIUM,
        confidence_factors={},
        category=SignalCategory.OTHER,
        geographic=GeographicContext(),
        temporal=TemporalContext(),
        impact_hints=ImpactHints(),
        evidence=[],
        ruleset_version="1.0.0",
        generated_at=datetime.utcnow(),
        signal_type=SignalType.UNCLASSIFIED,
        status=SignalStatus.ACTIVE,
    )


def test_signal_event_schema_version_constant():
    """SCHEMA_VERSION is defined and stable."""
    assert SCHEMA_VERSION == "1.0.0"


def test_signal_event_from_omen_signal():
    """SignalEvent.from_omen_signal builds envelope from OmenSignal."""
    signal = _make_minimal_signal()
    observed = datetime(2026, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
    event = SignalEvent.from_omen_signal(
        signal=signal,
        input_event_hash="sha256:abc123",
        observed_at=observed,
    )
    assert event.signal_id == "OMEN-TEST123"
    assert event.deterministic_trace_id == "trace123abc"
    assert event.input_event_hash == "sha256:abc123"
    assert event.source_event_id == "test-event"
    assert event.ruleset_version == "1.0.0"
    assert event.schema_version == SCHEMA_VERSION
    assert event.observed_at == observed
    assert event.emitted_at is not None
    assert event.signal is signal
    assert event.ledger_partition is None
    assert event.ledger_sequence is None
    assert event.ledger_written_at is None


def test_signal_event_with_ledger_metadata():
    """with_ledger_metadata returns copy with partition and sequence."""
    signal = _make_minimal_signal()
    event = SignalEvent.from_omen_signal(
        signal=signal,
        input_event_hash="sha256:def",
        observed_at=datetime.now(timezone.utc),
    )
    updated = event.with_ledger_metadata(partition="2026-01-15", sequence=42)
    assert updated.ledger_partition == "2026-01-15"
    assert updated.ledger_sequence == 42
    assert updated.ledger_written_at is not None
    assert event.ledger_partition is None
    assert event.ledger_sequence is None


def test_ledger_record_create_and_verify():
    """LedgerRecord.create produces record; verify() passes when intact."""
    signal = _make_minimal_signal()
    event = SignalEvent.from_omen_signal(
        signal=signal,
        input_event_hash="sha256:abc123",
        observed_at=datetime.now(timezone.utc),
    )
    record = LedgerRecord.create(event)
    assert record.checksum.startswith("crc32:")
    assert record.length > 0
    assert record.signal is event
    assert record.verify() is True


def test_ledger_record_verify_fails_when_tampered():
    """LedgerRecord.verify() returns False if payload was modified."""
    signal = _make_minimal_signal()
    event = SignalEvent.from_omen_signal(
        signal=signal,
        input_event_hash="sha256:abc",
        observed_at=datetime.now(timezone.utc),
    )
    record = LedgerRecord.create(event)
    # Tamper: use object.__setattr__ to bypass frozen model protection
    # This simulates what could happen if data was corrupted at storage/network level
    object.__setattr__(record.signal.signal, "title", "Tampered Title")
    assert record.verify() is False


def test_generate_input_event_hash_deterministic():
    """generate_input_event_hash is deterministic for same input."""
    data = {"a": 1, "b": 2, "ts": "2026-01-15"}
    h1 = generate_input_event_hash(data)
    h2 = generate_input_event_hash(data)
    assert h1 == h2
    assert h1.startswith("sha256:")


def test_generate_input_event_hash_key_order_independent():
    """Hash is same regardless of key order in dict."""
    h1 = generate_input_event_hash({"a": 1, "b": 2})
    h2 = generate_input_event_hash({"b": 2, "a": 1})
    assert h1 == h2


def test_import_signal_event_and_ledger_record():
    """SignalEvent and LedgerRecord are importable from domain.models."""
    from omen.domain.models import (
        SignalEvent,
        LedgerRecord,
        SCHEMA_VERSION,
        generate_input_event_hash,
    )

    assert SignalEvent is not None
    assert LedgerRecord is not None
    assert SCHEMA_VERSION == "1.0.0"
    assert callable(generate_input_event_hash)
