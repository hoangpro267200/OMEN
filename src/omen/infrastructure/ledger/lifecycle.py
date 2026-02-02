"""
Ledger Lifecycle Manager

Manages:
- Auto-sealing partitions
- Compressing old segments
- Archiving cold partitions
- Deleting expired partitions
- Storage statistics
"""

import gzip
import json
import logging
import os
import shutil
import tarfile
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from omen.config import RetentionConfig

logger = logging.getLogger(__name__)


@dataclass
class LifecyclePartitionInfo:
    """Information about a partition for lifecycle."""

    date: str
    path: Path
    is_sealed: bool
    is_late: bool
    is_compressed: bool
    total_size_bytes: int
    record_count: int
    segment_count: int
    last_modified: datetime


@dataclass
class StorageStats:
    """Storage statistics."""

    hot_partitions: int = 0
    hot_size_bytes: int = 0
    warm_partitions: int = 0
    warm_size_bytes: int = 0
    cold_partitions: int = 0
    cold_size_bytes: int = 0
    total_records: int = 0
    oldest_partition: Optional[str] = None
    newest_partition: Optional[str] = None


class LedgerLifecycleManager:
    """
    Manages ledger lifecycle operations.

    Usage:
        manager = LedgerLifecycleManager(base_path, config)
        await manager.run_lifecycle_tasks()
    """

    def __init__(
        self,
        base_path: Path | str,
        config: "RetentionConfig",
        archive_path: Optional[Path | str] = None,
    ) -> None:
        self.base_path = Path(base_path)
        self.config = config
        self.archive_path = Path(archive_path) if archive_path else self.base_path / "_archive"

    # ═══════════════════════════════════════════════════════════════════════════
    # Main Entry Points
    # ═══════════════════════════════════════════════════════════════════════════

    async def run_lifecycle_tasks(self) -> dict:
        """
        Run all lifecycle tasks.

        Returns:
            Summary of actions taken
        """
        logger.info("Starting ledger lifecycle tasks...")

        results: dict = {
            "sealed": [],
            "compressed": [],
            "archived": [],
            "deleted": [],
            "errors": [],
        }

        try:
            sealed = await self.auto_seal_partitions()
            results["sealed"] = sealed

            compressed = await self.compress_old_segments()
            results["compressed"] = compressed

            archived = await self.archive_cold_partitions()
            results["archived"] = archived

            deleted = await self.delete_expired_partitions()
            results["deleted"] = deleted
        except Exception as e:
            logger.error("Lifecycle task error: %s", e)
            results["errors"].append(str(e))

        logger.info("Lifecycle tasks completed: %s", results)
        return results

    # ═══════════════════════════════════════════════════════════════════════════
    # Auto-Seal
    # ═══════════════════════════════════════════════════════════════════════════

    async def auto_seal_partitions(self) -> list[str]:
        """Seal partitions that are past the seal threshold."""
        sealed: list[str] = []
        now = datetime.now(timezone.utc)

        for partition in self._list_partitions():
            if partition.is_sealed:
                continue

            should_seal = False
            partition_dt = self._parse_partition_date(partition.date)

            if partition.is_late:
                threshold = now - timedelta(days=self.config.late_seal_after_days)
                should_seal = partition_dt < threshold
            else:
                seal_time = partition_dt + timedelta(
                    hours=self.config.auto_seal_after_hours + self.config.seal_grace_period_hours
                )
                should_seal = now > seal_time

            if should_seal:
                try:
                    await self._seal_partition(partition)
                    sealed.append(partition.date)
                    logger.info("Auto-sealed partition: %s", partition.date)
                except Exception as e:
                    logger.error("Failed to seal %s: %s", partition.date, e)

        return sealed

    async def _seal_partition(self, partition: LifecyclePartitionInfo) -> None:
        """Seal a partition."""
        sealed_marker = partition.path / "_SEALED"
        sealed_marker.write_text(
            datetime.now(timezone.utc).isoformat(),
            encoding="utf-8",
        )
        for segment in partition.path.glob("signals-*.wal*"):
            if segment.suffix == ".gz":
                continue
            try:
                os.chmod(segment, 0o444)
            except OSError as e:
                logger.warning("Could not chmod %s: %s", segment, e)

    # ═══════════════════════════════════════════════════════════════════════════
    # Compression
    # ═══════════════════════════════════════════════════════════════════════════

    async def compress_old_segments(self) -> list[str]:
        """Compress segments older than threshold (sealed only)."""
        compressed: list[str] = []
        threshold = datetime.now(timezone.utc) - timedelta(days=self.config.compress_after_days)

        for partition in self._list_partitions():
            if not partition.is_sealed:
                continue
            partition_dt = self._parse_partition_date(partition.date)
            if partition_dt >= threshold:
                continue

            for segment in partition.path.glob("signals-*.wal"):
                if segment.suffix == ".gz":
                    continue
                try:
                    await self._compress_segment(segment)
                    compressed.append(str(segment))
                    logger.info("Compressed: %s", segment.name)
                except Exception as e:
                    logger.error("Failed to compress %s: %s", segment, e)

        return compressed

    async def _compress_segment(self, segment: Path) -> None:
        """Compress a single segment file."""
        compressed_path = segment.with_suffix(segment.suffix + ".gz")
        level = getattr(self.config, "compression_level", 6)

        with open(segment, "rb") as f_in:
            with gzip.open(compressed_path, "wb", compresslevel=level) as f_out:
                shutil.copyfileobj(f_in, f_out)

        if compressed_path.exists() and compressed_path.stat().st_size > 0:
            segment.unlink()
        else:
            if compressed_path.exists():
                compressed_path.unlink()
            raise OSError(f"Compression verification failed for {segment}")

    # ═══════════════════════════════════════════════════════════════════════════
    # Archive
    # ═══════════════════════════════════════════════════════════════════════════

    async def archive_cold_partitions(self) -> list[str]:
        """Move cold partitions to archive (sealed only)."""
        archived: list[str] = []
        threshold = datetime.now(timezone.utc) - timedelta(days=self.config.cold_retention_days)

        for partition in self._list_partitions():
            if not partition.is_sealed:
                continue
            partition_dt = self._parse_partition_date(partition.date)
            if partition_dt >= threshold:
                continue
            try:
                await self._archive_partition(partition)
                archived.append(partition.date)
                logger.info("Archived: %s", partition.date)
            except Exception as e:
                logger.error("Failed to archive %s: %s", partition.date, e)

        return archived

    async def _archive_partition(self, partition: LifecyclePartitionInfo) -> None:
        """Archive a single partition (move to archive dir or tar.gz)."""
        self.archive_path.mkdir(parents=True, exist_ok=True)
        dest = self.archive_path / partition.date
        fmt = getattr(self.config, "archive_format", "directory")

        if fmt == "tar.gz":
            tar_path = self.archive_path / f"{partition.date}.tar.gz"
            with tarfile.open(tar_path, "w:gz") as tar:
                tar.add(partition.path, arcname=partition.date)
            shutil.rmtree(partition.path)
        else:
            if dest.exists():
                shutil.rmtree(dest)
            shutil.copytree(partition.path, dest)
            shutil.rmtree(partition.path)

    # ═══════════════════════════════════════════════════════════════════════════
    # Deletion
    # ═══════════════════════════════════════════════════════════════════════════

    async def delete_expired_partitions(self) -> list[str]:
        """Delete partitions past retention period."""
        deleted: list[str] = []
        if not getattr(self.config, "delete_after_days", None):
            return deleted

        threshold = datetime.now(timezone.utc) - timedelta(days=self.config.delete_after_days)

        for base in [self.base_path, self.archive_path]:
            if not base.exists():
                continue
            for item in base.iterdir():
                if not item.is_dir():
                    continue
                if item.name.startswith("_"):
                    continue
                try:
                    date_str = item.name.split("-late")[0]
                    partition_dt = self._parse_partition_date(date_str)
                    if partition_dt < threshold:
                        shutil.rmtree(item)
                        deleted.append(item.name)
                        logger.warning("Deleted expired partition: %s", item.name)
                except (ValueError, OSError) as e:
                    logger.error("Error processing %s: %s", item, e)

        return deleted

    # ═══════════════════════════════════════════════════════════════════════════
    # Statistics
    # ═══════════════════════════════════════════════════════════════════════════

    def get_storage_stats(self) -> StorageStats:
        """Get comprehensive storage statistics."""
        stats = StorageStats()
        now = datetime.now(timezone.utc)
        hot_threshold = now - timedelta(days=self.config.hot_retention_days)
        warm_threshold = now - timedelta(days=self.config.warm_retention_days)
        all_dates: list[str] = []

        for partition in self._list_partitions():
            partition_dt = self._parse_partition_date(partition.date)
            all_dates.append(partition.date)

            if partition_dt >= hot_threshold:
                stats.hot_partitions += 1
                stats.hot_size_bytes += partition.total_size_bytes
            elif partition_dt >= warm_threshold:
                stats.warm_partitions += 1
                stats.warm_size_bytes += partition.total_size_bytes
            else:
                stats.cold_partitions += 1
                stats.cold_size_bytes += partition.total_size_bytes
            stats.total_records += partition.record_count

        if all_dates:
            stats.oldest_partition = min(all_dates)
            stats.newest_partition = max(all_dates)
        return stats

    # ═══════════════════════════════════════════════════════════════════════════
    # Helpers
    # ═══════════════════════════════════════════════════════════════════════════

    def _list_partitions(self) -> list[LifecyclePartitionInfo]:
        """List all partitions with metadata."""
        partitions: list[LifecyclePartitionInfo] = []
        if not self.base_path.exists():
            return partitions
        for item in sorted(self.base_path.iterdir()):
            if not item.is_dir():
                continue
            if item.name.startswith("_"):
                continue
            try:
                partitions.append(self._get_partition_info(item))
            except Exception as e:
                logger.warning("Could not read partition %s: %s", item, e)
        return partitions

    def _get_partition_info(self, path: Path) -> LifecyclePartitionInfo:
        """Get information about a partition."""
        is_sealed = (path / "_SEALED").exists()
        is_late = path.name.endswith("-late")
        segments = list(path.glob("signals-*.wal*"))
        is_compressed = any(s.suffix == ".gz" for s in segments)
        total_size = sum(s.stat().st_size for s in segments)

        record_count = 0
        manifest_path = path / "_manifest.json"
        if manifest_path.exists():
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                record_count = manifest.get("total_records", 0)
            except (json.JSONDecodeError, OSError):
                pass

        try:
            mtime = path.stat().st_mtime
            last_modified = datetime.fromtimestamp(mtime, tz=timezone.utc)
        except OSError:
            last_modified = datetime.now(timezone.utc)

        return LifecyclePartitionInfo(
            date=path.name,
            path=path,
            is_sealed=is_sealed,
            is_late=is_late,
            is_compressed=is_compressed,
            total_size_bytes=total_size,
            record_count=record_count,
            segment_count=len(segments),
            last_modified=last_modified,
        )

    def _parse_partition_date(self, date_str: str) -> datetime:
        """Parse partition date string to datetime."""
        date_str = date_str.split("-late")[0]
        return datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
