"""
Activity feed endpoint for real-time log.
"""

import uuid
from collections import deque
from datetime import datetime, timedelta
from typing import Literal

from fastapi import APIRouter, Query
from pydantic import BaseModel

router = APIRouter(prefix="/activity", tags=["Activity"])

_activity_log: deque = deque(maxlen=100)


class ActivityItem(BaseModel):
    """Single activity item."""
    id: str
    type: Literal["signal", "validation", "rule", "alert", "source", "error"]
    message: str
    timestamp: datetime
    details: dict = {}


@router.get("", response_model=list[ActivityItem])
async def get_activity(limit: int = Query(default=20, le=100)) -> list[ActivityItem]:
    """Get recent activity."""
    items = list(_activity_log)
    return items[-limit:]


def log_activity(
    activity_type: str,
    message: str,
    details: dict | None = None,
) -> None:
    """Log an activity item (call from pipeline/services)."""
    item = ActivityItem(
        id=str(uuid.uuid4())[:8],
        type=activity_type,  # type: ignore[arg-type]
        message=message,
        timestamp=datetime.utcnow(),
        details=details or {},
    )
    _activity_log.append(item)


def _init_demo_activity() -> None:
    """Pre-populate demo activity."""
    now = datetime.utcnow()
    demo = [
        ("signal", "Tín hiệu được tạo: OMEN-RS2024-001"),
        ("validation", "Sự kiện đã được xác thực: polymarket-0x7b2d..."),
        ("rule", "Quy tắc được áp dụng: liquidity_validation"),
        ("alert", "Cảnh báo mức độ nghiêm trọng CAO đã được kích hoạt"),
        ("source", "Polymarket: Đã nhận được 189 sự kiện mới"),
        ("signal", "Tín hiệu được tạo: OMEN-PC2024-002"),
        ("validation", "Sự kiện đã được xác thực: polymarket-0x8c3f..."),
        ("rule", "Quy tắc được áp dụng: geographic_relevance"),
        ("alert", "Cảnh báo mức độ nghiêm trọng TRUNG BÌNH đã được kích hoạt"),
        ("source", "Polymarket: Đã nhận được 234 sự kiện mới"),
    ]
    for i, (atype, msg) in enumerate(demo):
        _activity_log.append(
            ActivityItem(
                id=f"demo-{i}",
                type=atype,  # type: ignore[arg-type]
                message=msg,
                timestamp=now - timedelta(minutes=i),
            )
        )


_init_demo_activity()
