"""External Polymarket API schemas."""

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class PolymarketEvent(BaseModel):
    """Polymarket event schema (stub)."""

    id: str
    title: str
    description: str
    created_at: datetime
    liquidity: Optional[float] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
