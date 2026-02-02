"""
Weather adapter configuration.
"""

from typing import Literal
from pydantic import BaseModel, Field


class WeatherConfig(BaseModel):
    """Weather adapter configuration."""

    # Provider selection
    provider: Literal["noaa", "openweather", "tomorrow_io", "mock"] = Field(
        default="mock",
        description="Weather data provider",
    )

    # NOAA (Free)
    noaa_api_key: str | None = Field(default=None)
    noaa_base_url: str = Field(default="https://api.weather.gov")

    # OpenWeather (Freemium)
    openweather_api_key: str | None = Field(default=None)
    openweather_base_url: str = Field(default="https://api.openweathermap.org/data/3.0")

    # Tomorrow.io (Paid)
    tomorrow_api_key: str | None = Field(default=None)

    # Monitored regions (shipping areas)
    monitored_regions: list[str] = Field(
        default=[
            "Western Pacific",
            "Eastern Pacific",
            "North Atlantic",
            "Indian Ocean",
            "South China Sea",
            "Mediterranean",
            "Gulf of Mexico",
            "Caribbean",
        ],
        description="Ocean regions to monitor for storms",
    )

    # Alert thresholds
    min_storm_category: int = Field(
        default=1,
        ge=1,
        le=5,
        description="Minimum storm category to generate alert",
    )
    min_wind_speed_kts: int = Field(
        default=34,
        description="Minimum wind speed (knots) for alert",
    )
    min_path_confidence: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Minimum forecast path confidence",
    )

    # Update frequency
    polling_interval_seconds: int = Field(
        default=1800,
        description="Polling interval (30 minutes default)",
    )

    class Config:
        env_prefix = "OMEN_WEATHER_"


# Major shipping lanes that could be affected by storms
SHIPPING_LANES = {
    "transpacific": {
        "name": "Trans-Pacific",
        "regions": ["Western Pacific", "Eastern Pacific"],
        "ports": ["CNSHA", "USLAX", "USLGB", "JPYOK", "KRPUS"],
    },
    "asia_europe": {
        "name": "Asia-Europe",
        "regions": ["South China Sea", "Indian Ocean", "Mediterranean"],
        "ports": ["CNSHA", "SGSIN", "NLRTM", "DEHAM"],
    },
    "transatlantic": {
        "name": "Trans-Atlantic",
        "regions": ["North Atlantic"],
        "ports": ["USNYC", "NLRTM", "DEHAM", "BEANR"],
    },
    "intra_asia": {
        "name": "Intra-Asia",
        "regions": ["South China Sea", "Western Pacific"],
        "ports": ["CNSHA", "HKHKG", "SGSIN", "VNSGN", "KRPUS"],
    },
}
