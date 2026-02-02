"""
Freight rate data schemas.
"""

from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field


class FreightRate(BaseModel):
    """Container freight rate for a specific route."""

    route: str = Field(..., description="Route code (e.g., 'SHA-LAX')")
    origin_port: str = Field(..., description="Origin port name")
    origin_code: str = Field(..., description="Origin port code")
    destination_port: str = Field(..., description="Destination port name")
    destination_code: str = Field(..., description="Destination port code")

    # Current rate
    rate_usd_per_feu: float = Field(..., description="Rate per 40-foot container")
    rate_usd_per_teu: float = Field(default=0.0, description="Rate per 20-foot container")

    # Historical comparison
    rate_1d_ago: float = Field(default=0.0, description="Rate 1 day ago")
    rate_7d_ago: float = Field(default=0.0, description="Rate 7 days ago")
    rate_30d_ago: float = Field(default=0.0, description="Rate 30 days ago")
    rate_90d_ago: float = Field(default=0.0, description="Rate 90 days ago")

    # Changes
    change_1d_pct: float = Field(default=0.0, description="1-day change %")
    change_7d_pct: float = Field(default=0.0, description="7-day change %")
    change_30d_pct: float = Field(default=0.0, description="30-day change %")
    change_90d_pct: float = Field(default=0.0, description="90-day change %")

    # Volume/capacity indicators
    booking_volume_index: float = Field(
        default=100.0,
        description="Booking volume relative to baseline (100 = normal)",
    )
    capacity_utilization_pct: float = Field(
        default=80.0,
        ge=0.0,
        le=100.0,
        description="Capacity utilization %",
    )

    # Market indicators
    spot_premium_pct: float = Field(
        default=0.0,
        description="Spot vs contract rate premium %",
    )
    blank_sailings: int = Field(
        default=0,
        description="Number of cancelled sailings this week",
    )

    # Anomaly detection
    is_spike: bool = Field(default=False, description="Rate spike detected")
    spike_severity: Literal["none", "low", "medium", "high", "extreme"] = Field(
        default="none",
    )

    timestamp: datetime = Field(..., description="Rate timestamp")


class FreightIndex(BaseModel):
    """Container freight index (FBX, SCFI, WCI)."""

    index_name: str = Field(..., description="Index name (FBX, SCFI, WCI)")
    index_value: float = Field(..., description="Current index value")

    # Changes
    change_1d_pct: float = Field(default=0.0)
    change_7d_pct: float = Field(default=0.0)
    change_30d_pct: float = Field(default=0.0)
    change_ytd_pct: float = Field(default=0.0)

    # Historical
    value_52w_high: float = Field(default=0.0, description="52-week high")
    value_52w_low: float = Field(default=0.0, description="52-week low")

    # Component routes
    routes: list[FreightRate] = Field(default_factory=list)

    timestamp: datetime = Field(..., description="Index timestamp")


class RouteCapacity(BaseModel):
    """Capacity indicators for a shipping route."""

    route: str = Field(..., description="Route code")

    # Capacity metrics
    total_capacity_teu: int = Field(..., description="Total weekly capacity (TEU)")
    utilized_capacity_teu: int = Field(default=0, description="Utilized capacity")
    utilization_pct: float = Field(default=80.0, description="Utilization %")

    # Sailings
    scheduled_sailings: int = Field(default=0, description="Scheduled sailings this week")
    blank_sailings: int = Field(default=0, description="Cancelled sailings")
    extra_loaders: int = Field(default=0, description="Extra loader vessels added")

    # Demand indicators
    booking_demand_index: float = Field(
        default=100.0,
        description="Booking demand (100 = normal)",
    )
    rollover_rate_pct: float = Field(
        default=5.0,
        description="Cargo rollover rate %",
    )

    # Analysis
    capacity_outlook: Literal["oversupply", "balanced", "tight", "severe_shortage"] = Field(
        default="balanced",
    )

    timestamp: datetime


class RateSpike(BaseModel):
    """Detected rate spike event."""

    spike_id: str = Field(..., description="Unique spike ID")
    route: str = Field(..., description="Affected route")

    # Spike details
    current_rate: float = Field(..., description="Current rate")
    previous_rate: float = Field(..., description="Rate before spike")
    change_pct: float = Field(..., description="Rate change %")
    period_days: int = Field(..., description="Period over which spike occurred")

    # Severity
    severity: Literal["low", "medium", "high", "extreme"] = Field(...)

    # Context
    likely_cause: str = Field(default="", description="Likely cause of spike")
    affected_region: str = Field(default="", description="Affected trade region")

    # Timestamps
    detected_at: datetime
    spike_started_at: datetime | None = None
