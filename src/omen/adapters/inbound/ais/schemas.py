"""
AIS data schemas.

Pydantic models for vessel tracking, port status, and chokepoint monitoring.
"""

from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field


class Vessel(BaseModel):
    """Single vessel information from AIS."""

    mmsi: int = Field(..., description="Maritime Mobile Service Identity (unique)")
    imo: int | None = Field(default=None, description="IMO number")
    name: str = Field(..., description="Vessel name")
    vessel_type: str = Field(..., description="Vessel type (Container Ship, Tanker, etc.)")

    # Position
    lat: float = Field(..., description="Latitude")
    lon: float = Field(..., description="Longitude")

    # Movement
    speed_knots: float = Field(default=0.0, description="Speed over ground in knots")
    course_degrees: float = Field(default=0.0, description="Course over ground in degrees")

    # Destination
    destination: str | None = Field(default=None, description="Reported destination port")
    eta: datetime | None = Field(default=None, description="Estimated time of arrival")

    # Vessel details
    flag: str = Field(default="", description="Flag state (country code)")
    length_m: int = Field(default=0, description="Length in meters")
    width_m: int = Field(default=0, description="Width (beam) in meters")
    draught_m: float = Field(default=0.0, description="Current draught in meters")

    # Metadata
    timestamp: datetime = Field(..., description="AIS message timestamp")

    @property
    def is_container_ship(self) -> bool:
        """Check if vessel is a container ship."""
        return "container" in self.vessel_type.lower()

    @property
    def is_tanker(self) -> bool:
        """Check if vessel is a tanker."""
        return "tanker" in self.vessel_type.lower()


class PortStatus(BaseModel):
    """Port congestion status."""

    # Identification
    port_code: str = Field(..., description="UN/LOCODE (e.g., SGSIN)")
    port_name: str = Field(..., description="Port name")
    country: str = Field(..., description="Country")
    region: str = Field(default="", description="Geographic region")

    # Location
    lat: float = Field(..., description="Port latitude")
    lon: float = Field(..., description="Port longitude")

    # Current status
    vessels_waiting: int = Field(..., description="Vessels waiting to berth")
    vessels_berthed: int = Field(default=0, description="Vessels currently at berth")
    vessels_at_anchor: int = Field(default=0, description="Vessels at anchor")
    avg_wait_time_hours: float = Field(..., description="Average wait time in hours")

    # Historical baseline
    normal_waiting: int = Field(..., description="Normal vessel count (30-day average)")
    normal_wait_time_hours: float = Field(..., description="Normal wait time (30-day average)")

    # Derived metrics
    congestion_ratio: float = Field(
        default=1.0,
        description="Ratio of current to normal (1.5 = 150% of normal)",
    )
    wait_time_ratio: float = Field(
        default=1.0,
        description="Ratio of current to normal wait time",
    )

    # Anomaly detection
    anomaly_detected: bool = Field(default=False, description="Whether anomaly detected")
    anomaly_severity: Literal["none", "low", "medium", "high", "critical"] = Field(
        default="none",
        description="Anomaly severity level",
    )

    # Metadata
    timestamp: datetime = Field(..., description="Data timestamp")
    data_quality: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Data quality score (0-1)",
    )

    def calculate_congestion_ratio(self) -> float:
        """Calculate congestion ratio."""
        if self.normal_waiting <= 0:
            return 1.0
        return self.vessels_waiting / self.normal_waiting

    def calculate_wait_time_ratio(self) -> float:
        """Calculate wait time ratio."""
        if self.normal_wait_time_hours <= 0:
            return 1.0
        return self.avg_wait_time_hours / self.normal_wait_time_hours


class ChokePointStatus(BaseModel):
    """Status of major shipping chokepoints."""

    # Identification
    name: str = Field(..., description="Chokepoint name (e.g., Suez Canal)")
    location: tuple[float, float] = Field(..., description="(lat, lon)")

    # Current status
    vessels_in_transit: int = Field(default=0, description="Vessels currently in transit")
    vessels_waiting: int = Field(default=0, description="Vessels waiting to transit")
    vessels_at_anchor: int = Field(default=0, description="Vessels at anchor nearby")
    avg_transit_time_hours: float = Field(..., description="Current average transit time")

    # Historical baseline
    normal_transit_time_hours: float = Field(..., description="Normal transit time")
    normal_daily_transits: int = Field(default=50, description="Normal daily transits")

    # Derived metrics
    delay_ratio: float = Field(
        default=1.0,
        description="Ratio of current to normal transit time",
    )
    queue_severity: Literal["none", "low", "medium", "high", "critical"] = Field(
        default="none",
        description="Queue severity level",
    )

    # Anomaly detection
    delays_detected: bool = Field(default=False, description="Whether delays detected")
    blockage_detected: bool = Field(default=False, description="Whether blockage detected")

    # Affected routes
    affected_routes: list[str] = Field(
        default_factory=list,
        description="Affected shipping routes",
    )

    # Metadata
    timestamp: datetime = Field(..., description="Data timestamp")
    data_source: str = Field(default="", description="Data source identifier")

    def calculate_delay_ratio(self) -> float:
        """Calculate delay ratio."""
        if self.normal_transit_time_hours <= 0:
            return 1.0
        return self.avg_transit_time_hours / self.normal_transit_time_hours


class VesselMovement(BaseModel):
    """Vessel movement tracking for route deviation detection."""

    mmsi: int = Field(..., description="Vessel MMSI")
    vessel_name: str = Field(..., description="Vessel name")

    # Expected route
    origin_port: str = Field(..., description="Origin port code")
    destination_port: str = Field(..., description="Destination port code")
    expected_route: list[tuple[float, float]] = Field(
        default_factory=list,
        description="Expected route waypoints (lat, lon)",
    )

    # Actual position
    current_lat: float = Field(..., description="Current latitude")
    current_lon: float = Field(..., description="Current longitude")

    # Deviation analysis
    deviation_km: float = Field(default=0.0, description="Deviation from expected route")
    deviation_detected: bool = Field(default=False, description="Whether deviation detected")
    deviation_type: Literal["none", "minor", "reroute", "emergency"] = Field(
        default="none",
        description="Type of deviation",
    )

    # Metadata
    timestamp: datetime = Field(..., description="Position timestamp")


class PortCongestionAlert(BaseModel):
    """Alert generated from port congestion detection."""

    alert_id: str = Field(..., description="Unique alert ID")
    port_code: str = Field(..., description="Affected port code")
    port_name: str = Field(..., description="Affected port name")

    # Severity
    severity: Literal["low", "medium", "high", "critical"] = Field(
        ...,
        description="Alert severity",
    )

    # Metrics
    vessels_waiting: int = Field(..., description="Vessels waiting")
    congestion_ratio: float = Field(..., description="Congestion ratio")
    wait_time_hours: float = Field(..., description="Average wait time")

    # Impact
    estimated_cargo_value_usd: float = Field(
        default=0.0,
        description="Estimated cargo value affected",
    )
    affected_vessel_count: int = Field(default=0, description="Number of vessels affected")

    # Timestamps
    detected_at: datetime = Field(..., description="When alert was generated")
    data_timestamp: datetime = Field(..., description="Underlying data timestamp")


class ChokePointAlert(BaseModel):
    """Alert generated from chokepoint monitoring."""

    alert_id: str = Field(..., description="Unique alert ID")
    chokepoint_name: str = Field(..., description="Chokepoint name")

    # Severity
    severity: Literal["low", "medium", "high", "critical"] = Field(
        ...,
        description="Alert severity",
    )

    # Status
    alert_type: Literal["delay", "congestion", "blockage", "reroute"] = Field(
        ...,
        description="Type of alert",
    )

    # Metrics
    vessels_waiting: int = Field(..., description="Vessels waiting")
    delay_hours: float = Field(..., description="Additional delay in hours")
    delay_ratio: float = Field(..., description="Delay ratio vs normal")

    # Impact
    affected_routes: list[str] = Field(
        default_factory=list,
        description="Affected shipping routes",
    )
    estimated_vessels_affected: int = Field(
        default=0,
        description="Estimated vessels affected globally",
    )

    # Timestamps
    detected_at: datetime = Field(..., description="When alert was generated")
    data_timestamp: datetime = Field(..., description="Underlying data timestamp")
