"""
Ledger Reader v2 — WAL Framing

Reads framed records with crash recovery.

Frame format:
  [4 bytes: payload_length (u32 big-endian)]
  [4 bytes: crc32 (u32 big-endian)]
  [N bytes: payload (JSON UTF-8)]

Recovery:
- Partial trailing frame is detected and skipped
- CRC mismatch is logged and skipped
"""

import json
import logging
import struct
import zlib
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Iterator, Optional

from omen.domain.models.signal_event import SignalEvent

logger = logging.getLogger(__name__)

FRAME_HEADER_SIZE = 8


@dataclass
class PartitionInfo:
    """Partition metadata."""

    partition_date: str
    is_sealed: bool
    is_late: bool
    total_records: int
    segments: list[str]
    sealed_at: Optional[datetime] = None
    highwater_sequence: int = 0
    manifest_revision: int = 0

    @property
    def total_signals(self) -> int:
        """Alias for total_records (Part 3 API compatibility)."""
        return self.total_records


class LedgerReader:
    """
    Read framed records from ledger.

    Features:
    - Crash recovery (partial frame detection)
    - CRC validation
    - Manifest-aware queries
    """

    def __init__(self, base_path: str | Path):
        self.base_path = Path(base_path)

    def list_partitions(self) -> list[PartitionInfo]:
        """List all partitions with metadata."""
        partitions = []
        if not self.base_path.exists():
            return partitions
        for partition_dir in sorted(self.base_path.iterdir()):
            if not partition_dir.is_dir():
                continue
            if partition_dir.name.startswith("_"):
                continue
            info = self._get_partition_info(partition_dir)
            if info:
                partitions.append(info)
        return partitions

    def _get_partition_info(self, partition_dir: Path) -> Optional[PartitionInfo]:
        """Get partition info from manifest or scan."""
        is_sealed = (partition_dir / "_SEALED").exists()
        manifest_file = partition_dir / "_manifest.json"

        if manifest_file.exists():
            manifest = json.loads(manifest_file.read_text())
            sealed_at = None
            if manifest.get("sealed_at"):
                sealed_at = datetime.fromisoformat(manifest["sealed_at"])
            return PartitionInfo(
                partition_date=partition_dir.name,
                is_sealed=is_sealed,
                is_late=manifest.get("is_late_partition", "-late" in partition_dir.name),
                total_records=manifest.get("total_records", 0),
                segments=[s["file"] for s in manifest.get("segments", [])],
                sealed_at=sealed_at,
                highwater_sequence=manifest.get("highwater_sequence", 0),
                manifest_revision=manifest.get("manifest_revision", 0),
            )

        segments = sorted(partition_dir.glob("signals-*.wal"))
        total = sum(self._count_records_in_segment(s) for s in segments)

        return PartitionInfo(
            partition_date=partition_dir.name,
            is_sealed=is_sealed,
            is_late="-late" in partition_dir.name,
            total_records=total,
            segments=[s.name for s in segments],
        )

    def is_partition_sealed(self, partition_date: str) -> bool:
        """Check if partition is sealed."""
        partition_dir = self.base_path / partition_date
        return (partition_dir / "_SEALED").exists()

    def read_partition(
        self,
        partition_date: str,
        validate: bool = True,
        include_late: bool = True,
    ) -> Iterator[SignalEvent]:
        """
        Read all signals from a partition.

        Args:
            partition_date: Partition to read (YYYY-MM-DD)
            validate: If True, verify CRC
            include_late: If True, also read -late partition
        """
        partition_dir = self.base_path / partition_date
        if partition_dir.exists():
            yield from self._read_partition_dir(partition_dir, validate)

        if include_late:
            late_dir = self.base_path / f"{partition_date}-late"
            if late_dir.exists():
                yield from self._read_partition_dir(late_dir, validate)

    def _read_partition_dir(
        self,
        partition_dir: Path,
        validate: bool,
    ) -> Iterator[SignalEvent]:
        """Read all segments in partition directory."""
        for segment in sorted(partition_dir.glob("signals-*.wal")):
            yield from self._read_segment(segment, validate)

    def _read_segment(
        self,
        segment_path: Path,
        validate: bool,
    ) -> Iterator[SignalEvent]:
        """Read framed records from segment file."""
        with open(segment_path, "rb") as f:
            record_num = 0

            while True:
                header = f.read(FRAME_HEADER_SIZE)

                if len(header) == 0:
                    break

                if len(header) < FRAME_HEADER_SIZE:
                    logger.warning(
                        "Partial header at end of %s (record %s), truncating",
                        segment_path.name,
                        record_num,
                    )
                    break

                length, expected_crc = struct.unpack(">II", header)
                payload = f.read(length)

                if len(payload) < length:
                    logger.warning(
                        "Partial payload at end of %s (record %s), truncating",
                        segment_path.name,
                        record_num,
                    )
                    break

                record_num += 1

                if validate:
                    actual_crc = zlib.crc32(payload) & 0xFFFFFFFF
                    if actual_crc != expected_crc:
                        logger.error(
                            "CRC mismatch in %s record %s: expected %08x, got %08x",
                            segment_path.name,
                            record_num,
                            expected_crc,
                            actual_crc,
                        )
                        continue

                try:
                    data = json.loads(payload.decode("utf-8"))
                    yield SignalEvent(**data)
                except (json.JSONDecodeError, Exception) as e:
                    logger.error(
                        "Invalid JSON in %s record %s: %s",
                        segment_path.name,
                        record_num,
                        e,
                    )
                    continue

    def _count_records_in_segment(self, segment_path: Path) -> int:
        """Count valid records in segment."""
        count = 0
        with open(segment_path, "rb") as f:
            while True:
                header = f.read(FRAME_HEADER_SIZE)
                if len(header) < FRAME_HEADER_SIZE:
                    break
                length, _ = struct.unpack(">II", header)
                payload = f.read(length)
                if len(payload) < length:
                    break
                count += 1
        return count

    def list_signal_ids(self, partition_date: str) -> list[str]:
        """List all signal_ids in partition (including late)."""
        return [
            event.signal_id
            for event in self.read_partition(partition_date, validate=False)
        ]

    def get_signal(
        self,
        partition_date: str,
        signal_id: str,
    ) -> Optional[SignalEvent]:
        """Get specific signal by ID."""
        for event in self.read_partition(partition_date):
            if event.signal_id == signal_id:
                return event
        return None

    def get_partition_highwater(self, partition_date: str) -> tuple[int, int]:
        """
        Get highwater mark for partition.

        Returns:
            (highwater_sequence, manifest_revision)
        """
        partition_dir = self.base_path / partition_date
        if not partition_dir.exists():
            return (0, 0)
        manifest_file = partition_dir / "_manifest.json"

        if manifest_file.exists():
            manifest = json.loads(manifest_file.read_text())
            return (
                manifest.get("highwater_sequence", 0),
                manifest.get("manifest_revision", 0),
            )

        count = sum(
            self._count_records_in_segment(s)
            for s in partition_dir.glob("signals-*.wal")
        )
        return (count, 0)

    def query_by_time_range(
        self,
        start: datetime,
        end: datetime,
        validate: bool = True,
    ) -> Iterator[SignalEvent]:
        """
        Query signals by time range.

        Uses emitted_at for filtering. Scans partitions that may contain
        signals in [start, end].
        """
        current = start.date()
        end_date = end.date()

        while current <= end_date:
            partition = current.isoformat()
            for event in self.read_partition(partition, validate=validate):
                if start <= event.emitted_at <= end:
                    yield event
            current = date.fromordinal(current.toordinal() + 1)

    def query_by_trace_ids(
        self,
        trace_ids: list[str],
        validate: bool = True,
    ) -> list[SignalEvent]:
        """Query signals by trace IDs (scans all partitions)."""
        trace_set = set(trace_ids)
        results: list[SignalEvent] = []

        for partition_info in self.list_partitions():
            for event in self.read_partition(
                partition_info.partition_date,
                validate=validate,
            ):
                if event.deterministic_trace_id in trace_set:
                    results.append(event)

        return results

    def query_by_category(
        self,
        category: str,
        start_date: date,
        end_date: date,
        validate: bool = True,
    ) -> Iterator[SignalEvent]:
        """Query signals by category within date range."""
        current = start_date

        while current <= end_date:
            partition = current.isoformat()
            for event in self.read_partition(partition, validate=validate):
                cat = event.signal.category
                if (cat.value if hasattr(cat, "value") else str(cat)) == category:
                    yield event
            current = date.fromordinal(current.toordinal() + 1)
