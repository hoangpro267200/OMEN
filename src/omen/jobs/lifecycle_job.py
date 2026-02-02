"""
Lifecycle Job

Runs ledger lifecycle tasks periodically.

Usage:
    python -m omen.jobs.lifecycle_job
    python -m omen.jobs.lifecycle_job --once
"""

import argparse
import asyncio
import logging
from pathlib import Path

from omen.config import get_config
from omen.infrastructure.ledger.lifecycle import LedgerLifecycleManager

logger = logging.getLogger(__name__)


async def run_lifecycle_once(base_path: Path) -> dict:
    """Run lifecycle tasks once."""
    config = get_config()
    manager = LedgerLifecycleManager(
        base_path,
        config.retention,
        archive_path=config.retention.archive_path,
    )
    results = await manager.run_lifecycle_tasks()

    stats = manager.get_storage_stats()
    logger.info("Storage stats:")
    logger.info(
        "  Hot: %s partitions, %.2f MB",
        stats.hot_partitions,
        stats.hot_size_bytes / 1024 / 1024,
    )
    logger.info(
        "  Warm: %s partitions, %.2f MB",
        stats.warm_partitions,
        stats.warm_size_bytes / 1024 / 1024,
    )
    logger.info(
        "  Cold: %s partitions, %.2f MB",
        stats.cold_partitions,
        stats.cold_size_bytes / 1024 / 1024,
    )
    logger.info("  Total records: %s", stats.total_records)
    return results


async def run_lifecycle_loop(
    base_path: Path,
    interval_hours: int = 24,
) -> None:
    """Run lifecycle tasks in a loop."""
    logger.info("Starting lifecycle loop (interval: %sh)", interval_hours)
    while True:
        try:
            await run_lifecycle_once(base_path)
        except Exception as e:
            logger.error("Lifecycle error: %s", e)
        await asyncio.sleep(interval_hours * 3600)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    parser = argparse.ArgumentParser(description="Ledger lifecycle management")
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    parser.add_argument(
        "--interval",
        type=int,
        default=24,
        help="Hours between runs",
    )
    parser.add_argument(
        "--base-path",
        default=None,
        help="Ledger base path (default: from config)",
    )
    args = parser.parse_args()

    config = get_config()
    base_path = Path(args.base_path or config.ledger_base_path)

    if args.once:
        asyncio.run(run_lifecycle_once(base_path))
    else:
        asyncio.run(run_lifecycle_loop(base_path, args.interval))


if __name__ == "__main__":
    main()
