"""Unit tests for framed ledger writer and reader."""

import os
import struct
from datetime import date, datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

from omen.domain.models.omen_signal import (
    OmenSignal,
    ConfidenceLevel,
    SignalCategory,
    GeographicContext,
    TemporalContext,
)
from omen.domain.models.impact_hints import ImpactHints
from omen.domain.models.signal_event import SignalEvent
from omen.domain.models.enums import SignalType, SignalStatus
from omen.infrastructure.ledger import LedgerWriter, LedgerReader, PartitionInfo
from omen.infrastructure.ledger.reader import FRAME_HEADER_SIZE
from omen.infrastructure.ledger.writer import LedgerWriteError, _atomic_write_text


def _make_minimal_signal(signal_id: str = "OMEN-FRAME001") -> OmenSignal:
    """Build a minimal valid OmenSignal for ledger tests."""
    return OmenSignal(
        signal_id=signal_id,
        source_event_id="frame-test",
        trace_id="trace-frame",
        title="Frame Test",
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
        generated_at=datetime.now(timezone.utc),
        signal_type=SignalType.UNCLASSIFIED,
        status=SignalStatus.ACTIVE,
    )


def _make_event(
    signal_id: str = "OMEN-FRAME001",
    trace_id: str = "trace-frame",
    category: SignalCategory = SignalCategory.OTHER,
) -> SignalEvent:
    """Build SignalEvent for ledger tests."""
    signal = _make_minimal_signal(signal_id=signal_id)
    signal = signal.model_copy(update={"trace_id": trace_id, "category": category})
    return SignalEvent.from_omen_signal(
        signal=signal,
        input_event_hash="sha256:frame123",
        observed_at=datetime.now(timezone.utc),
    )


def test_framed_write_read(tmp_path: Path):
    """Write SignalEvent and read back; WAL files exist."""
    writer = LedgerWriter(tmp_path)
    reader = LedgerReader(tmp_path)

    event = _make_event()
    result = writer.write(event)

    assert result.ledger_partition is not None
    assert result.ledger_sequence is not None
    assert result.ledger_written_at is not None

    signals = list(reader.read_partition(result.ledger_partition))
    assert len(signals) >= 1
    assert signals[-1].signal_id == "OMEN-FRAME001"

    wal_files = list((tmp_path / result.ledger_partition).glob("*.wal"))
    assert len(wal_files) > 0


def test_read_partition_validate_crc(tmp_path: Path):
    """Read with validate=True still yields valid records."""
    writer = LedgerWriter(tmp_path)
    reader = LedgerReader(tmp_path)
    result = writer.write(_make_event("OMEN-CRC001"))
    partition = result.ledger_partition or ""
    signals = list(reader.read_partition(partition, validate=True))
    assert len(signals) == 1
    assert signals[0].signal_id == "OMEN-CRC001"


def test_list_partitions(tmp_path: Path):
    """list_partitions returns partition info."""
    writer = LedgerWriter(tmp_path)
    writer.write(_make_event("OMEN-LIST001"))
    reader = LedgerReader(tmp_path)
    partitions = reader.list_partitions()
    assert len(partitions) >= 1
    assert all(isinstance(p, PartitionInfo) for p in partitions)


def test_list_signal_ids(tmp_path: Path):
    """list_signal_ids returns written signal_ids."""
    writer = LedgerWriter(tmp_path)
    result = writer.write(_make_event("OMEN-ID001"))
    reader = LedgerReader(tmp_path)
    ids = reader.list_signal_ids(result.ledger_partition or "")
    assert "OMEN-ID001" in ids


def test_get_signal(tmp_path: Path):
    """get_signal returns event by id."""
    writer = LedgerWriter(tmp_path)
    result = writer.write(_make_event("OMEN-GET001"))
    reader = LedgerReader(tmp_path)
    found = reader.get_signal(result.ledger_partition or "", "OMEN-GET001")
    assert found is not None
    assert found.signal_id == "OMEN-GET001"
    assert reader.get_signal(result.ledger_partition or "", "nonexistent") is None


def test_rollover_creates_new_segment(tmp_path: Path):
    """When MAX_SEGMENT_RECORDS is reached, new segment is created."""
    import omen.infrastructure.ledger.writer as wmod

    original_max = wmod.MAX_SEGMENT_RECORDS
    try:
        wmod.MAX_SEGMENT_RECORDS = 3
        writer = LedgerWriter(tmp_path)
        for i in range(5):
            writer.write(_make_event(f"OMEN-R{i:03d}"))

        partition_dirs = [d for d in tmp_path.iterdir() if d.is_dir() and not d.name.startswith("_")]
        assert len(partition_dirs) >= 1
        segments = list(partition_dirs[0].glob("signals-*.wal"))
        assert len(segments) >= 2
    finally:
        wmod.MAX_SEGMENT_RECORDS = original_max


def test_current_pointer_exists(tmp_path: Path):
    """_CURRENT file points to active segment."""
    writer = LedgerWriter(tmp_path)
    writer.write(_make_event())
    partition_dirs = [d for d in tmp_path.iterdir() if d.is_dir() and not d.name.startswith("_")]
    assert len(partition_dirs) == 1
    current_file = partition_dirs[0] / "_CURRENT"
    assert current_file.exists()
    segment_name = current_file.read_text().strip()
    assert segment_name.endswith(".wal")


def test_partial_frame_truncation(tmp_path: Path):
    """Reader skips partial trailing frame (crash recovery)."""
    writer = LedgerWriter(tmp_path)
    event = _make_event("OMEN-PARTIAL")
    result = writer.write(event)
    partition_dir = tmp_path / (result.ledger_partition or "")
    segment = next(partition_dir.glob("signals-*.wal"))

    # Append partial header (4 bytes only) to simulate crash
    with open(segment, "ab") as f:
        f.write(b"\x00\x00\x00\x01")  # length=1, incomplete header

    reader = LedgerReader(tmp_path)
    signals = list(reader.read_partition(result.ledger_partition or "", validate=True))
    assert len(signals) == 1
    assert signals[0].signal_id == "OMEN-PARTIAL"


def test_get_partition_highwater(tmp_path: Path):
    """get_partition_highwater returns count before seal."""
    writer = LedgerWriter(tmp_path)
    result = writer.write(_make_event("OMEN-HW1"))
    partition = result.ledger_partition or ""
    reader = LedgerReader(tmp_path)
    hw, rev = reader.get_partition_highwater(partition)
    assert hw >= 1
    assert rev == 0


def test_partition_info_total_signals(tmp_path: Path):
    """PartitionInfo.total_signals is alias for total_records."""
    writer = LedgerWriter(tmp_path)
    writer.write(_make_event("OMEN-SIG1"))
    reader = LedgerReader(tmp_path)
    partitions = reader.list_partitions()
    assert len(partitions) >= 1
    assert partitions[0].total_signals == partitions[0].total_records
    assert partitions[0].total_signals >= 1


def test_query_by_time_range(tmp_path: Path):
    """query_by_time_range yields events with emitted_at in range."""
    writer = LedgerWriter(tmp_path)
    writer.write(_make_event("OMEN-T1"))
    writer.write(_make_event("OMEN-T2"))
    reader = LedgerReader(tmp_path)
    start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    end = datetime.now(timezone.utc)
    events = list(reader.query_by_time_range(start, end, validate=True))
    assert len(events) >= 2
    for e in events:
        assert start <= e.emitted_at <= end


def test_query_by_trace_ids(tmp_path: Path):
    """query_by_trace_ids returns events matching trace IDs."""
    writer = LedgerWriter(tmp_path)
    writer.write(_make_event("OMEN-TR1", trace_id="trace-a"))
    writer.write(_make_event("OMEN-TR2", trace_id="trace-b"))
    writer.write(_make_event("OMEN-TR3", trace_id="trace-c"))
    reader = LedgerReader(tmp_path)
    results = reader.query_by_trace_ids(["trace-a", "trace-c"], validate=True)
    assert len(results) == 2
    trace_ids = {e.deterministic_trace_id for e in results}
    assert trace_ids == {"trace-a", "trace-c"}


def test_query_by_category(tmp_path: Path):
    """query_by_category yields events with matching signal category."""
    writer = LedgerWriter(tmp_path)
    writer.write(_make_event("OMEN-CAT1", category=SignalCategory.GEOPOLITICAL))
    writer.write(_make_event("OMEN-CAT2", category=SignalCategory.OTHER))
    writer.write(_make_event("OMEN-CAT3", category=SignalCategory.GEOPOLITICAL))
    reader = LedgerReader(tmp_path)
    # Use UTC date since events are timestamped with UTC
    utc_today = datetime.now(timezone.utc).date()
    events = list(
        reader.query_by_category(
            SignalCategory.GEOPOLITICAL.value,
            utc_today,
            utc_today,
            validate=True,
        )
    )
    assert len(events) == 2
    for e in events:
        assert e.signal.category == SignalCategory.GEOPOLITICAL


def test_ledger_crash_tail_returns_n_minus_1_valid_records(tmp_path: Path):
    """
    MANDATORY: Ledger crash-tail test.
    Write N records, truncate last segment to simulate partial frame;
    reader MUST stop safely and return N-1 valid records (no corrupted record).
    """
    writer = LedgerWriter(tmp_path)
    reader = LedgerReader(tmp_path)
    N = 3
    for i in range(N):
        writer.write(_make_event(f"OMEN-CRASH{i}"))
    partition_dir = tmp_path / list(tmp_path.iterdir())[0].name
    segment = next(partition_dir.glob("signals-*.wal"))
    # Truncate after 2 complete frames
    with open(segment, "r+b") as f:
        pos = 0
        for _ in range(2):
            header = f.read(FRAME_HEADER_SIZE)
            if len(header) < FRAME_HEADER_SIZE:
                break
            length, _ = struct.unpack(">II", header)
            f.read(length)
            pos = f.tell()
        f.truncate(pos)
    partition_date = partition_dir.name
    signals = list(reader.read_partition(partition_date, validate=True))
    assert len(signals) == 2, "Reader must return N-1 valid records after truncation"
    assert signals[0].signal_id == "OMEN-CRASH0"
    assert signals[1].signal_id == "OMEN-CRASH1"


def test_ledger_sequence_monotonic_across_rollover(tmp_path: Path):
    """
    MANDATORY: ledger_sequence is strictly increasing within partition across segments.
    Set MAX_SEGMENT_RECORDS small to force rollover; write 7 events; assert monotonic.
    """
    import omen.infrastructure.ledger.writer as wmod

    original_max = wmod.MAX_SEGMENT_RECORDS
    try:
        wmod.MAX_SEGMENT_RECORDS = 3
        writer = LedgerWriter(tmp_path)
        reader = LedgerReader(tmp_path)
        sequences: list[int] = []
        for i in range(7):
            event = _make_event(f"OMEN-SEQ{i:03d}")
            result = writer.write(event)
            assert result.ledger_sequence is not None
            sequences.append(result.ledger_sequence)

        assert len(sequences) == 7
        for j in range(1, len(sequences)):
            assert sequences[j] > sequences[j - 1], (
                f"ledger_sequence must be strictly increasing: "
                f"{sequences[j - 1]} -> {sequences[j]}"
            )

        partition = result.ledger_partition or ""
        signals = list(reader.read_partition(partition, validate=True))
        assert len(signals) == 7
        read_sequences = [s.ledger_sequence for s in signals if s.ledger_sequence is not None]
        assert read_sequences == sequences

        # T1: monotonic across process restart (new writer instance, same partition)
        writer2 = LedgerWriter(tmp_path)
        for i in range(7, 10):
            result2 = writer2.write(_make_event(f"OMEN-SEQ{i:03d}"))
            assert result2.ledger_sequence is not None
            sequences.append(result2.ledger_sequence)
        assert len(sequences) == 10
        for j in range(1, len(sequences)):
            assert sequences[j] > sequences[j - 1], (
                f"ledger_sequence must be strictly increasing across restart: "
                f"{sequences[j - 1]} -> {sequences[j]}"
            )
    finally:
        wmod.MAX_SEGMENT_RECORDS = original_max


def test_atomic_write_text_fsync_order(tmp_path: Path):
    """T2: _atomic_write_text calls fsync(temp) before replace, then fsync(dir) after replace."""
    path = tmp_path / "f"
    calls: list[str] = []

    real_fsync = os.fsync
    real_replace = os.replace

    def tracked_fsync(fd):
        calls.append("fsync")
        real_fsync(fd)

    def tracked_replace(src, dst):
        calls.append("replace")
        real_replace(src, dst)

    with patch("os.fsync", side_effect=tracked_fsync), patch(
        "os.replace", side_effect=tracked_replace
    ):
        _atomic_write_text(path, "x")
    assert "fsync" in calls
    assert "replace" in calls
    idx_first_fsync = calls.index("fsync")
    idx_replace = calls.index("replace")
    assert idx_first_fsync < idx_replace, "fsync(temp) must happen before replace"


def test_writer_raises_ledger_write_error_on_io_failure(tmp_path: Path):
    """T3: Writer raises LedgerWriteError (not bare OSError) for IO failures."""
    writer = LedgerWriter(tmp_path)
    event = _make_event("OMEN-ERR")

    with patch("builtins.open", side_effect=OSError(28, "No space left on device")):
        with pytest.raises(LedgerWriteError) as exc_info:
            writer.write(event)
        assert "No space" in str(exc_info.value) or "28" in str(exc_info.value)


def test_signal_event_naive_datetime_raises():
    """T4: SignalEvent with naive emitted_at must raise ValueError at validation."""
    from omen.domain.models.signal_event import SignalEvent

    signal = _make_minimal_signal("OMEN-NAIVE")
    with pytest.raises(ValueError, match="timezone-aware"):
        SignalEvent(
            signal_id=signal.signal_id,
            deterministic_trace_id=signal.trace_id,
            input_event_hash="sha256:x",
            source_event_id=signal.source_event_id,
            ruleset_version=signal.ruleset_version,
            observed_at=datetime.now(timezone.utc),
            emitted_at=datetime.utcnow(),
            signal=signal,
        )


def test_signal_event_json_z_suffix_timezone_aware():
    """T4: Deserialize from JSON with Z suffix -> timezone-aware UTC."""
    from omen.domain.models.signal_event import SignalEvent

    signal = _make_minimal_signal("OMEN-Z")
    event = SignalEvent.from_omen_signal(
        signal=signal,
        input_event_hash="sha256:z",
        observed_at=datetime.now(timezone.utc),
    )
    data = event.model_dump(mode="json")
    data["emitted_at"] = "2026-01-15T12:00:00Z"
    data["observed_at"] = "2026-01-15T11:00:00Z"
    restored = SignalEvent.model_validate(data)
    assert restored.emitted_at.tzinfo is not None
    assert restored.observed_at.tzinfo is not None
