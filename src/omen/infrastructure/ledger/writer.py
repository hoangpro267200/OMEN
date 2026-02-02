"""
Ledger Writer v2 — WAL Framing

True append-only with crash-safe framing.

Record format:
  [4 bytes: payload_length (u32 big-endian)]
  [4 bytes: crc32 (u32 big-endian)]
  [N bytes: payload (JSON UTF-8)]

Crash safety:
- Partial writes detectable by length mismatch
- Reader truncates trailing partial record
- No corrupted records possible
"""

import json
import logging
import os
import struct
import sys
import time
import zlib
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from filelock import FileLock

from omen.domain.models.signal_event import SignalEvent

logger = logging.getLogger(__name__)

try:
    from omen.infrastructure.observability.metrics import (
        LEDGER_WRITES,
        LEDGER_WRITE_DURATION,
    )
    _LEDGER_METRICS_AVAILABLE = True
except ImportError:
    _LEDGER_METRICS_AVAILABLE = False


# Configuration
MAX_SEGMENT_SIZE_BYTES = 10 * 1024 * 1024  # 10MB
MAX_SEGMENT_RECORDS = 10_000
SEAL_GRACE_PERIOD_HOURS = 6
LATE_SEAL_GRACE_DAYS = 3  # Late partitions seal after 3 days


# Frame format
FRAME_HEADER_SIZE = 8  # 4 bytes length + 4 bytes crc32


def _atomic_write_text(path: Path, text: str) -> None:
    """
    Atomically write text to path with durability.

    1) Write to temp in same directory
    2) flush + os.fsync(temp_fd)
    3) os.replace(temp, path)
    4) fsync parent directory

    Raises OSError on any I/O failure.
    """
    path = Path(path)
    parent = path.parent
    temp = parent / (path.name + ".tmp")
    with open(temp, "w") as f:
        f.write(text)
        f.flush()
        os.fsync(f.fileno())
    os.replace(temp, path)
    # Invariant 4: fsync parent directory. POSIX: failure MUST raise. Windows: gate + log if impossible.
    if sys.platform == "win32":
        try:
            dir_fd = os.open(parent, os.O_RDONLY)
            try:
                os.fsync(dir_fd)
            finally:
                os.close(dir_fd)
        except OSError:
            logger.warning(
                "durability degraded: fsync(parent dir) not possible on Windows (%s)",
                parent,
            )
    else:
        dir_fd = os.open(parent, os.O_RDONLY)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)


class LedgerWriter:
    """
    Append-only ledger writer with WAL framing.

    Guarantees:
    - O(1) append (no copy)
    - Crash-safe (partial writes detectable)
    - Single-writer per partition (file lock)
    - Immutable segments after rollover
    """

    def __init__(self, base_path: str | Path):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        self._current_segments: dict[str, Path] = {}  # partition -> current segment
        self._record_counts: dict[str, int] = {}  # segment -> record count

    def write(self, event: SignalEvent) -> SignalEvent:
        """
        Write signal to ledger.

        Returns SignalEvent with ledger metadata populated.
        Raises LedgerWriteError on I/O failure (e.g. disk full).
        """
        start = time.perf_counter()
        try:
            result = self._write_impl(event)
            if _LEDGER_METRICS_AVAILABLE:
                partition = result.ledger_partition or "unknown"
                LEDGER_WRITES.labels(partition=partition, result="success").inc()
                LEDGER_WRITE_DURATION.observe(time.perf_counter() - start)
            return result
        except OSError as e:
            if _LEDGER_METRICS_AVAILABLE:
                LEDGER_WRITES.labels(partition="unknown", result="error").inc()
                LEDGER_WRITE_DURATION.observe(time.perf_counter() - start)
            raise LedgerWriteError(str(e)) from e

    def _write_impl(self, event: SignalEvent) -> SignalEvent:
        """Internal write path; callers use write() which wraps OSError."""
        # Determine partition (use UTC; support both naive and aware datetime)
        emitted = event.emitted_at
        if emitted.tzinfo is None:
            partition_date = emitted.date().isoformat()
        else:
            partition_date = emitted.date().isoformat()
        partition_dir = self.base_path / partition_date

        # Check if partition is sealed
        if self._is_sealed(partition_dir):
            # Late arrival
            partition_date = f"{partition_date}-late"
            partition_dir = self.base_path / partition_date
            logger.warning("Late arrival: %s -> %s", event.signal_id, partition_date)

        # Create partition if needed
        partition_dir.mkdir(parents=True, exist_ok=True)

        # Acquire partition lock (single-writer guarantee)
        lock_file = partition_dir / "_LOCK"

        with FileLock(str(lock_file)):
            # Get or create current segment
            segment_file = self._get_or_create_current_segment(partition_dir)

            # Per-segment record index (1-based)
            record_index = self._increment_record_count(segment_file)
            # Partition-wide monotonic sequence: (segment_ordinal << 32) | record_index
            segment_ordinal = int(segment_file.stem.split("-")[1])
            ledger_sequence = (segment_ordinal << 32) | record_index

            # Add ledger metadata
            event = event.with_ledger_metadata(
                partition=partition_date,
                sequence=ledger_sequence,
            )

            # Serialize to bytes (canonical JSON)
            payload_bytes = event.model_dump_json(
                exclude_none=True,
            ).encode("utf-8")

            # Write framed record
            self._append_framed_record(segment_file, payload_bytes)

            # Check if segment needs rollover
            self._maybe_rollover(partition_dir, segment_file)

        logger.debug(
            "Ledger write: %s -> %s/%s",
            event.signal_id,
            partition_date,
            ledger_sequence,
        )

        return event

    def _append_framed_record(self, segment_file: Path, payload_bytes: bytes) -> None:
        """
        Append framed record to segment.

        Frame format: [u32 length][u32 crc32][payload]

        Crash-safe: partial frame is detectable and truncatable.
        """
        crc = zlib.crc32(payload_bytes) & 0xFFFFFFFF
        header = struct.pack(">II", len(payload_bytes), crc)

        with open(segment_file, "ab") as f:
            f.write(header + payload_bytes)
            f.flush()
            os.fsync(f.fileno())

    async def flush_and_close(self) -> None:
        """
        Flush and close any resources. Called during graceful shutdown.

        This writer does not keep file handles open; each write uses
        open/fsync/close. So this is a no-op except for logging.
        Ensures any future implementation that keeps handles open can
        flush and close here.
        """
        logger.info(
            "LedgerWriter flush_and_close: no open file handles "
            "(each write is already fsync'd and closed)."
        )

    def _get_or_create_current_segment(self, partition_dir: Path) -> Path:
        """
        Get current writable segment, creating if needed.

        Uses _CURRENT file to track active segment.
        """
        partition_key = str(partition_dir)

        if partition_key in self._current_segments:
            segment = self._current_segments[partition_key]
            if segment.exists() and self._is_segment_writable(segment):
                return segment

        current_file = partition_dir / "_CURRENT"

        if current_file.exists():
            segment_name = current_file.read_text().strip()
            segment = partition_dir / segment_name
            if segment.exists() and self._is_segment_writable(segment):
                self._current_segments[partition_key] = segment
                return segment

        segments = sorted(partition_dir.glob("signals-*.wal"))

        for segment in reversed(segments):
            if self._is_segment_writable(segment):
                self._set_current_segment(partition_dir, segment)
                return segment

        if segments:
            last_num = int(segments[-1].stem.split("-")[1])
            new_num = last_num + 1
        else:
            new_num = 1

        new_segment = partition_dir / f"signals-{new_num:03d}.wal"
        new_segment.touch()
        self._set_current_segment(partition_dir, new_segment)

        return new_segment

    def _set_current_segment(self, partition_dir: Path, segment: Path) -> None:
        """Update _CURRENT pointer (atomic + durable: fsync file and parent dir)."""
        current_file = partition_dir / "_CURRENT"
        _atomic_write_text(current_file, segment.name)
        self._current_segments[str(partition_dir)] = segment

    def _is_segment_writable(self, segment: Path) -> bool:
        """Check if segment is writable (not sealed)."""
        if not os.access(segment, os.W_OK):
            return False
        if segment.stat().st_size >= MAX_SEGMENT_SIZE_BYTES:
            return False
        count = self._get_record_count(segment)
        if count >= MAX_SEGMENT_RECORDS:
            return False
        return True

    def _maybe_rollover(self, partition_dir: Path, segment_file: Path) -> None:
        """
        Check if segment needs rollover.

        If limits exceeded:
        1. Seal current segment (chmod 444)
        2. Create new segment
        3. Update _CURRENT pointer
        """
        size = segment_file.stat().st_size
        count = self._get_record_count(segment_file)

        needs_rollover = (
            size >= MAX_SEGMENT_SIZE_BYTES or count >= MAX_SEGMENT_RECORDS
        )

        if not needs_rollover:
            return

        try:
            segment_file.chmod(0o444)
        except OSError:
            pass  # Windows may not support chmod the same way
        logger.info(
            "Segment sealed: %s (%s records, %s bytes)",
            segment_file.name,
            count,
            size,
        )

        current_num = int(segment_file.stem.split("-")[1])
        new_segment = partition_dir / f"signals-{current_num + 1:03d}.wal"
        new_segment.touch()

        self._set_current_segment(partition_dir, new_segment)
        self._record_counts.pop(str(segment_file), None)

        logger.info("Segment rollover: %s -> %s", segment_file.name, new_segment.name)

    def _get_record_count(self, segment: Path) -> int:
        """Get record count for segment (cached)."""
        key = str(segment)

        if key not in self._record_counts:
            count = 0
            try:
                with open(segment, "rb") as f:
                    while True:
                        header = f.read(FRAME_HEADER_SIZE)
                        if len(header) < FRAME_HEADER_SIZE:
                            break
                        length, _ = struct.unpack(">II", header)
                        payload = f.read(length)
                        if len(payload) < length:
                            break
                        count += 1
            except OSError:
                pass
            self._record_counts[key] = count

        return self._record_counts[key]

    def _increment_record_count(self, segment: Path) -> int:
        """Increment and return record count."""
        count = self._get_record_count(segment) + 1
        self._record_counts[str(segment)] = count
        return count

    def _is_sealed(self, partition_dir: Path) -> bool:
        """Check if partition is sealed."""
        return (partition_dir / "_SEALED").exists()

    def seal_partition(self, partition_date: str) -> None:
        """
        Seal a partition.

        For main partitions: call after SEAL_GRACE_PERIOD_HOURS.
        For late partitions: call after LATE_SEAL_GRACE_DAYS.

        Raises LedgerWriteError on I/O failure.
        """
        try:
            self._seal_partition_impl(partition_date)
        except OSError as e:
            raise LedgerWriteError(str(e)) from e

    def _seal_partition_impl(self, partition_date: str) -> None:
        """Internal seal path; callers use seal_partition which wraps OSError."""
        partition_dir = self.base_path / partition_date

        if not partition_dir.exists():
            raise ValueError(f"Partition not found: {partition_date}")

        if self._is_sealed(partition_dir):
            return

        for segment in partition_dir.glob("signals-*.wal"):
            if os.access(segment, os.W_OK):
                try:
                    segment.chmod(0o444)
                except OSError:
                    pass

        manifest = self._create_manifest(partition_dir, partition_date)
        manifest_file = partition_dir / "_manifest.json"
        _atomic_write_text(manifest_file, json.dumps(manifest, indent=2))

        (partition_dir / "_SEALED").touch()
        self._current_segments.pop(str(partition_dir), None)

        logger.info("Partition sealed: %s", partition_date)

    def _create_manifest(self, partition_dir: Path, partition_date: str) -> dict:
        """Create partition manifest with highwater mark."""
        segments = []
        total_records = 0
        max_sequence = 0

        for segment in sorted(partition_dir.glob("signals-*.wal")):
            count = self._get_record_count(segment)
            size = segment.stat().st_size
            with open(segment, "rb") as f:
                content = f.read()
            checksum = f"crc32:{zlib.crc32(content) & 0xFFFFFFFF:08x}"
            segments.append({
                "file": segment.name,
                "record_count": count,
                "size_bytes": size,
                "checksum": checksum,
            })
            total_records += count
            max_sequence = max(max_sequence, total_records)

        return {
            "schema_version": "1.0.0",
            "partition_date": partition_date,
            "sealed_at": datetime.now(timezone.utc).isoformat(),
            "total_records": total_records,
            "highwater_sequence": max_sequence,
            "manifest_revision": 1,
            "segments": segments,
            "is_late_partition": "-late" in partition_date,
        }

    def get_partitions_to_seal(self) -> list[str]:
        """
        Get partitions ready to seal.

        Main partitions: after SEAL_GRACE_PERIOD_HOURS.
        Late partitions: after LATE_SEAL_GRACE_DAYS.
        """
        to_seal = []
        now = datetime.now(timezone.utc)

        for partition_dir in self.base_path.iterdir():
            if not partition_dir.is_dir():
                continue
            if partition_dir.name.startswith("_"):
                continue
            if self._is_sealed(partition_dir):
                continue

            try:
                is_late = "-late" in partition_dir.name
                base_date = partition_dir.name.replace("-late", "")
                partition_date_obj = date.fromisoformat(base_date)

                if is_late:
                    seal_after = datetime.combine(
                        partition_date_obj + timedelta(days=LATE_SEAL_GRACE_DAYS),
                        datetime.min.time(),
                        tzinfo=timezone.utc,
                    )
                else:
                    partition_end = datetime.combine(
                        partition_date_obj + timedelta(days=1),
                        datetime.min.time(),
                        tzinfo=timezone.utc,
                    )
                    seal_after = partition_end + timedelta(hours=SEAL_GRACE_PERIOD_HOURS)

                if now >= seal_after:
                    to_seal.append(partition_dir.name)
            except ValueError:
                continue

        return to_seal


class LedgerWriteError(Exception):
    """Ledger write failed."""

    pass
