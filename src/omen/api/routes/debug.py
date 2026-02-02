"""
Debug endpoints for pipeline visibility.

Security: Requires DEBUG scope (admin-level access).
"""

from typing import Literal, Optional

from fastapi import APIRouter, Depends, Query

from omen.infrastructure.debug.rejection_tracker import get_rejection_tracker
from omen.infrastructure.security.auth import verify_api_key
from omen.infrastructure.security.rbac import Scopes, require_scopes

router = APIRouter(prefix="/debug", tags=["Debug"])

# Security dependencies for debug routes
_debug_deps = [Depends(verify_api_key), Depends(require_scopes([Scopes.DEBUG]))]


@router.get("/rejections", dependencies=_debug_deps)
async def get_rejections(
    limit: int = Query(default=50, le=200),
    stage: Optional[
        Literal["ingestion", "mapping", "validation", "translation", "generation"]
    ] = None,
):
    """
    Get recent rejected events with reasons.

    Use this to understand WHY events are being filtered out.

    **Requires scope:** `debug`
    """
    tracker = get_rejection_tracker()
    return {
        "rejections": tracker.get_recent_rejections(limit=limit, stage=stage),
        "statistics": tracker.get_statistics(),
    }


@router.get("/passed", dependencies=_debug_deps)
async def get_passed(limit: int = Query(default=50, le=200)):
    """
    Get recently passed/generated signals.

    **Requires scope:** `debug`
    """
    tracker = get_rejection_tracker()
    return {
        "passed": tracker.get_recent_passed(limit=limit),
        "total_passed": tracker.get_passed_count(),
    }


@router.get("/statistics", dependencies=_debug_deps)
async def get_pipeline_statistics():
    """
    Get overall pipeline statistics.

    Shows pass/rejection rates and breakdown by stage.

    **Requires scope:** `debug`
    """
    tracker = get_rejection_tracker()
    return tracker.get_statistics()


@router.delete("/data", dependencies=_debug_deps)
async def clear_debug_data():
    """
    Clear all debug records.

    **Requires scope:** `debug`
    """
    tracker = get_rejection_tracker()
    tracker.clear()
    return {"status": "cleared"}
