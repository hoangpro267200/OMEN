"""
Debug endpoints for pipeline visibility.
"""

from typing import Literal, Optional

from fastapi import APIRouter, Query

from omen.infrastructure.debug.rejection_tracker import get_rejection_tracker

router = APIRouter(prefix="/debug", tags=["Debug"])


@router.get("/rejections")
async def get_rejections(
    limit: int = Query(default=50, le=200),
    stage: Optional[
        Literal["ingestion", "mapping", "validation", "translation", "generation"]
    ] = None,
):
    """
    Get recent rejected events with reasons.

    Use this to understand WHY events are being filtered out.
    """
    tracker = get_rejection_tracker()
    return {
        "rejections": tracker.get_recent_rejections(limit=limit, stage=stage),
        "statistics": tracker.get_statistics(),
    }


@router.get("/passed")
async def get_passed(limit: int = Query(default=50, le=200)):
    """Get recently passed/generated signals."""
    tracker = get_rejection_tracker()
    return {
        "passed": tracker.get_recent_passed(limit=limit),
        "total_passed": tracker.get_passed_count(),
    }


@router.get("/statistics")
async def get_pipeline_statistics():
    """
    Get overall pipeline statistics.

    Shows pass/rejection rates and breakdown by stage.
    """
    tracker = get_rejection_tracker()
    return tracker.get_statistics()


@router.post("/clear")
async def clear_debug_data():
    """Clear all debug records."""
    tracker = get_rejection_tracker()
    tracker.clear()
    return {"status": "cleared"}
