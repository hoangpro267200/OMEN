"""
Weather data schemas.
"""

from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field


class StormAlert(BaseModel):
    """Tropical cyclone / typhoon / hurricane alert."""

    storm_id: str = Field(..., description="Unique storm identifier")
    name: str = Field(..., description="Storm name (e.g., 'Haiyan')")
    storm_type: Literal["tropical_storm", "hurricane", "typhoon", "cyclone"] = Field(
        ...,
        description="Type of storm",
    )
    category: int = Field(
        ...,
        ge=0,
        le=5,
        description="Saffir-Simpson scale (0 = tropical storm, 1-5 = hurricane)",
    )

    # Current position
    lat: float = Field(..., description="Current latitude")
    lon: float = Field(..., description="Current longitude")

    # Intensity
    wind_speed_kts: int = Field(..., description="Maximum sustained winds (knots)")
    wind_speed_mph: int = Field(default=0, description="Wind speed in mph")
    pressure_mb: int = Field(..., description="Central pressure (millibars)")

    # Movement
    movement_speed_kts: float = Field(default=0.0, description="Storm movement speed")
    movement_direction_deg: float = Field(default=0.0, description="Storm direction")

    # Forecast path (list of (lat, lon, datetime) tuples)
    forecast_path: list[tuple[float, float, str]] = Field(
        default_factory=list,
        description="Forecast path waypoints",
    )
    path_confidence: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Forecast path confidence",
    )

    # Impact estimation
    affected_shipping_lanes: list[str] = Field(
        default_factory=list,
        description="Affected shipping routes",
    )
    affected_ports: list[str] = Field(
        default_factory=list,
        description="Ports in storm path",
    )
    estimated_vessels_at_risk: int = Field(
        default=0,
        description="Estimated vessels needing to reroute",
    )

    # Advisory info
    advisory_number: str = Field(default="", description="NHC/JTWC advisory number")

    timestamp: datetime = Field(..., description="Data timestamp")


class WeatherWarning(BaseModel):
    """General severe weather warning."""

    warning_id: str = Field(..., description="Unique warning ID")
    warning_type: Literal["storm", "fog", "ice", "high_seas", "gale", "hurricane"] = Field(
        ...,
        description="Type of warning",
    )
    severity: Literal["advisory", "watch", "warning", "emergency"] = Field(
        ...,
        description="Severity level",
    )

    # Affected area
    region: str = Field(..., description="Affected region name")
    area_description: str = Field(default="", description="Detailed area description")

    # Optional polygon
    area_polygon: list[tuple[float, float]] = Field(
        default_factory=list,
        description="Affected area polygon (lat, lon)",
    )

    # Timing
    start_time: datetime = Field(..., description="Warning start time")
    end_time: datetime | None = Field(default=None, description="Warning end time")

    # Impact
    affected_ports: list[str] = Field(default_factory=list)
    affected_routes: list[str] = Field(default_factory=list)

    # Description
    headline: str = Field(..., description="Warning headline")
    description: str = Field(default="", description="Full description")

    timestamp: datetime = Field(..., description="Issue timestamp")


class SeaConditions(BaseModel):
    """Sea state conditions for shipping areas."""

    region: str = Field(..., description="Ocean region")

    # Wave conditions
    wave_height_m: float = Field(..., description="Significant wave height (meters)")
    wave_period_s: float = Field(default=0.0, description="Wave period (seconds)")
    wave_direction_deg: float = Field(default=0.0, description="Wave direction")

    # Wind
    wind_speed_kts: float = Field(..., description="Wind speed (knots)")
    wind_direction_deg: float = Field(default=0.0, description="Wind direction")

    # Sea state (Douglas scale 0-9)
    sea_state: int = Field(
        default=0,
        ge=0,
        le=9,
        description="Douglas sea state scale",
    )

    # Visibility
    visibility_nm: float = Field(default=10.0, description="Visibility (nautical miles)")

    # Conditions assessment
    conditions: Literal["calm", "moderate", "rough", "very_rough", "high", "phenomenal"] = Field(
        default="moderate",
        description="Overall conditions",
    )
    navigation_advisory: str = Field(default="", description="Advisory for vessels")

    timestamp: datetime = Field(..., description="Observation timestamp")


class StormForecast(BaseModel):
    """Extended storm forecast."""

    storm_id: str
    name: str

    # 5-day forecast
    forecasts: list[dict] = Field(
        default_factory=list,
        description="List of forecast points",
    )

    # Confidence cone
    cone_points: list[tuple[float, float]] = Field(
        default_factory=list,
        description="Uncertainty cone polygon",
    )

    # Intensity forecast
    intensity_forecast: list[dict] = Field(
        default_factory=list,
        description="Intensity forecast over time",
    )

    timestamp: datetime
