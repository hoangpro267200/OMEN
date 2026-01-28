"""
Activity feed endpoint — real events from pipeline execution.

No pre-populated demo data. Activity is empty until the pipeline or sources run.
"""

from typing import Literal, Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel

from omen.infrastructure.activity.activity_logger import get_activity_logger


router = APIRouter(prefix="/activity", tags=["Activity"])

ActivityType = Literal["signal", "validation", "rule", "alert", "source", "error", "system"]


class ActivityItemResponse(BaseModel):
    """Single activity item from the system."""

    id: str
    type: ActivityType
    message: str
    timestamp: str
    details: dict = {}


@router.get("", response_model=list[ActivityItemResponse])
async def get_activity(
    limit: int = Query(default=50, le=200, description="Maximum items to return"),
    type_filter: Optional[str] = Query(
        default=None,
        description="Filter by type: signal, validation, rule, alert, source, error, system",
    ),
) -> list[ActivityItemResponse]:
    """
    Get recent activity from the OMEN system.

    All activity comes from real pipeline execution and source fetches:
    - signal: When signals are generated
    - validation: When events pass or fail validation
    - rule: When translation rules are applied
    - alert: When high-severity signals are created
    - source: When data is fetched from sources
    - error: When errors occur

    If the pipeline has not run, the list is empty.
    """
    logger = get_activity_logger()
    events = logger.get_recent(limit=limit)

    if type_filter:
        events = [e for e in events if e.get("type") == type_filter]

    return [
        ActivityItemResponse(
            id=e["id"],
            type=e["type"],  # type: ignore[arg-type]
            message=e["message"],
            timestamp=e["timestamp"],
            details=e.get("details", {}),
        )
        for e in events
    ]


@router.get("/types")
async def get_activity_types() -> dict[str, str]:
    """Return available activity types and short descriptions."""
    return {
        "signal": "Signal generation events",
        "validation": "Event validation results",
        "rule": "Translation rule applications",
        "alert": "High-severity alerts",
        "source": "Data source fetch events",
        "error": "System errors",
        "system": "General system events",
    }
