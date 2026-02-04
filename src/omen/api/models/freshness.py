"""
Data Freshness Models for API Responses.

Provides standardized freshness tracking across all API endpoints.
Ensures consumers know how recent the data is.
"""

from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Generic, Optional, TypeVar

from pydantic import BaseModel, Field, computed_field

from omen.application.ports.time_provider import utc_now


class FreshnessLevel(str, Enum):
    """Data freshness classification."""

    REAL_TIME = "real_time"      # < 1 second
    FRESH = "fresh"             # < 1 minute
    RECENT = "recent"           # < 5 minutes
    ACCEPTABLE = "acceptable"   # < 15 minutes
    STALE = "stale"             # < 1 hour
    OUTDATED = "outdated"       # > 1 hour


class DataFreshness(BaseModel):
    """
    Data freshness metadata for API responses.

    Included in all data responses to indicate data age.
    """

    observed_at: datetime = Field(
        ...,
        description="When the data was originally observed/collected"
    )
    fetched_at: datetime = Field(
        default_factory=utc_now,
        description="When the data was fetched for this response"
    )
    source: str = Field(
        ...,
        description="Data source identifier"
    )
    freshness_level: FreshnessLevel = Field(
        default=FreshnessLevel.FRESH,
        description="Qualitative freshness classification"
    )
    data_age_seconds: float = Field(
        default=0.0,
        ge=0.0,
        description="Age of data in seconds"
    )
    is_cached: bool = Field(
        default=False,
        description="Whether this data came from cache"
    )
    cache_ttl_seconds: Optional[int] = Field(
        default=None,
        description="Remaining cache TTL if cached"
    )

    model_config = {"frozen": True}

    @classmethod
    def calculate(
        cls,
        observed_at: datetime,
        source: str,
        is_cached: bool = False,
        cache_ttl_seconds: Optional[int] = None,
    ) -> "DataFreshness":
        """Calculate freshness from observed timestamp."""
        now = utc_now()
        
        # Ensure timezone aware
        if observed_at.tzinfo is None:
            from datetime import timezone
            observed_at = observed_at.replace(tzinfo=timezone.utc)
        
        age = (now - observed_at).total_seconds()
        
        # Determine freshness level
        if age < 1:
            level = FreshnessLevel.REAL_TIME
        elif age < 60:
            level = FreshnessLevel.FRESH
        elif age < 300:
            level = FreshnessLevel.RECENT
        elif age < 900:
            level = FreshnessLevel.ACCEPTABLE
        elif age < 3600:
            level = FreshnessLevel.STALE
        else:
            level = FreshnessLevel.OUTDATED

        return cls(
            observed_at=observed_at,
            fetched_at=now,
            source=source,
            freshness_level=level,
            data_age_seconds=age,
            is_cached=is_cached,
            cache_ttl_seconds=cache_ttl_seconds,
        )


T = TypeVar("T")


class FreshResponse(BaseModel, Generic[T]):
    """
    Generic response wrapper with freshness metadata.

    Usage:
        @router.get("/signals", response_model=FreshResponse[list[Signal]])
        async def get_signals():
            signals = await fetch_signals()
            return FreshResponse.create(
                data=signals,
                source="polymarket",
                observed_at=earliest_signal_time,
            )
    """

    data: T = Field(..., description="Response data")
    freshness: DataFreshness = Field(..., description="Data freshness metadata")
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional response metadata"
    )

    @classmethod
    def create(
        cls,
        data: T,
        source: str,
        observed_at: Optional[datetime] = None,
        is_cached: bool = False,
        cache_ttl_seconds: Optional[int] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> "FreshResponse[T]":
        """Create a fresh response with automatic freshness calculation."""
        if observed_at is None:
            observed_at = utc_now()

        freshness = DataFreshness.calculate(
            observed_at=observed_at,
            source=source,
            is_cached=is_cached,
            cache_ttl_seconds=cache_ttl_seconds,
        )

        return cls(
            data=data,
            freshness=freshness,
            metadata=metadata or {},
        )


class PaginatedFreshResponse(BaseModel, Generic[T]):
    """
    Paginated response with freshness metadata.
    """

    items: list[T] = Field(..., description="Page items")
    total: int = Field(..., ge=0, description="Total item count")
    page: int = Field(..., ge=1, description="Current page number")
    page_size: int = Field(..., ge=1, description="Items per page")
    has_more: bool = Field(..., description="Whether more pages exist")
    freshness: DataFreshness = Field(..., description="Data freshness metadata")

    @computed_field
    @property
    def total_pages(self) -> int:
        """Calculate total number of pages."""
        if self.page_size <= 0:
            return 0
        return (self.total + self.page_size - 1) // self.page_size

    @classmethod
    def create(
        cls,
        items: list[T],
        total: int,
        page: int,
        page_size: int,
        source: str,
        observed_at: Optional[datetime] = None,
    ) -> "PaginatedFreshResponse[T]":
        """Create paginated response with freshness."""
        if observed_at is None:
            observed_at = utc_now()

        freshness = DataFreshness.calculate(
            observed_at=observed_at,
            source=source,
        )

        has_more = (page * page_size) < total

        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            has_more=has_more,
            freshness=freshness,
        )


class MultiSourceFreshness(BaseModel):
    """
    Aggregated freshness from multiple sources.
    """

    sources: dict[str, DataFreshness] = Field(
        default_factory=dict,
        description="Freshness per source"
    )
    overall_level: FreshnessLevel = Field(
        default=FreshnessLevel.FRESH,
        description="Overall freshness (worst of all sources)"
    )
    oldest_data_age_seconds: float = Field(
        default=0.0,
        description="Age of oldest data"
    )
    newest_data_age_seconds: float = Field(
        default=0.0,
        description="Age of newest data"
    )

    @classmethod
    def aggregate(
        cls,
        source_freshness: dict[str, DataFreshness],
    ) -> "MultiSourceFreshness":
        """Aggregate freshness from multiple sources."""
        if not source_freshness:
            return cls()

        ages = [f.data_age_seconds for f in source_freshness.values()]
        levels = [f.freshness_level for f in source_freshness.values()]

        # Overall level is the worst (most stale)
        level_order = list(FreshnessLevel)
        overall_level = max(levels, key=lambda l: level_order.index(l))

        return cls(
            sources=source_freshness,
            overall_level=overall_level,
            oldest_data_age_seconds=max(ages),
            newest_data_age_seconds=min(ages),
        )
