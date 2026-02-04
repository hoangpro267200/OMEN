"""Storage and lifecycle API routes."""

from dataclasses import asdict
from typing import Any

from fastapi import APIRouter, Depends

from omen.api.route_dependencies import require_storage_read, require_storage_write
from omen.config import get_config
from omen.infrastructure.ledger.lifecycle import LedgerLifecycleManager, StorageStats
from omen.infrastructure.security.unified_auth import AuthContext

router = APIRouter(tags=["storage"])


@router.get("/storage/stats")
async def get_storage_stats(
    auth: AuthContext = Depends(require_storage_read),  # RBAC: read:storage
) -> dict[str, Any]:
    """Get ledger storage statistics."""
    config = get_config()
    manager = LedgerLifecycleManager(
        config.ledger_base_path,
        config.retention,
        archive_path=config.retention.archive_path,
    )
    stats: StorageStats = manager.get_storage_stats()
    return {
        "stats": asdict(stats),
        "config": {
            "hot_retention_days": config.retention.hot_retention_days,
            "warm_retention_days": config.retention.warm_retention_days,
            "cold_retention_days": config.retention.cold_retention_days,
            "delete_after_days": config.retention.delete_after_days,
        },
    }


@router.post("/storage/lifecycle/tasks")
async def create_lifecycle_tasks(
    auth: AuthContext = Depends(require_storage_write),  # RBAC: write:storage
) -> dict[str, Any]:
    """Create and run lifecycle tasks (seal, compress, archive, delete)."""
    config = get_config()
    manager = LedgerLifecycleManager(
        config.ledger_base_path,
        config.retention,
        archive_path=config.retention.archive_path,
    )
    results = await manager.run_lifecycle_tasks()
    return {
        "status": "completed",
        "results": results,
    }
