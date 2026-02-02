"""
AIS adapter configuration.

Supports multiple providers:
- AISHub (free, limited)
- MarineTraffic (paid, comprehensive)
- VesselFinder (paid, alternative)
"""

from typing import Literal
from pydantic import BaseModel, Field


class AISConfig(BaseModel):
    """AIS adapter configuration."""

    # Provider selection
    provider: Literal["aishub", "marinetraffic", "vesselfinder", "mock"] = Field(
        default="mock",
        description="AIS data provider",
    )

    # AISHub (Free tier)
    aishub_username: str | None = Field(
        default=None,
        description="AISHub username for API access",
    )

    # MarineTraffic (Paid)
    marinetraffic_api_key: str | None = Field(
        default=None,
        description="MarineTraffic API key",
    )
    marinetraffic_base_url: str = Field(
        default="https://services.marinetraffic.com/api",
        description="MarineTraffic API base URL",
    )

    # VesselFinder (Alternative)
    vesselfinder_api_key: str | None = Field(
        default=None,
        description="VesselFinder API key",
    )

    # Monitored ports (major container ports)
    monitored_ports: list[str] = Field(
        default=[
            "SGSIN",  # Singapore
            "CNSHA",  # Shanghai
            "CNNGB",  # Ningbo
            "CNYTN",  # Shenzhen (Yantian)
            "HKHKG",  # Hong Kong
            "KRPUS",  # Busan
            "USNYC",  # New York/New Jersey
            "USLAX",  # Los Angeles
            "USLGB",  # Long Beach
            "NLRTM",  # Rotterdam
            "DEHAM",  # Hamburg
            "BEANR",  # Antwerp
            "AEJEA",  # Jebel Ali (Dubai)
            "VNSGN",  # Ho Chi Minh City (Cat Lai)
            "VNHPH",  # Hai Phong
        ],
        description="Port codes to monitor for congestion",
    )

    # Monitored chokepoints
    monitored_chokepoints: list[str] = Field(
        default=[
            "Suez Canal",
            "Panama Canal",
            "Strait of Malacca",
            "Strait of Hormuz",
            "Bab el-Mandeb",
            "Bosphorus",
            "Cape of Good Hope",
        ],
        description="Major shipping chokepoints to monitor",
    )

    # Anomaly detection thresholds
    congestion_threshold_multiplier: float = Field(
        default=1.5,
        description="Congestion ratio threshold (1.5 = 150% of normal)",
    )
    route_deviation_threshold_km: float = Field(
        default=100.0,
        description="Route deviation threshold in kilometers",
    )
    wait_time_threshold_multiplier: float = Field(
        default=1.5,
        description="Wait time threshold (1.5 = 150% of normal)",
    )

    # Update frequency
    polling_interval_seconds: int = Field(
        default=300,
        description="Polling interval in seconds (5 minutes default)",
    )

    # Data freshness
    max_data_age_hours: float = Field(
        default=1.0,
        description="Maximum acceptable data age in hours",
    )

    # Rate limiting
    max_requests_per_minute: int = Field(
        default=60,
        description="Maximum API requests per minute",
    )

    class Config:
        env_prefix = "OMEN_AIS_"


# Port metadata for enrichment
PORT_METADATA: dict[str, dict] = {
    "SGSIN": {
        "name": "Singapore",
        "country": "Singapore",
        "region": "Southeast Asia",
        "lat": 1.2644,
        "lon": 103.8201,
        "normal_waiting": 25,
        "normal_wait_hours": 12.0,
    },
    "CNSHA": {
        "name": "Shanghai",
        "country": "China",
        "region": "East Asia",
        "lat": 31.3584,
        "lon": 121.5886,
        "normal_waiting": 40,
        "normal_wait_hours": 24.0,
    },
    "CNNGB": {
        "name": "Ningbo-Zhoushan",
        "country": "China",
        "region": "East Asia",
        "lat": 29.9339,
        "lon": 121.8776,
        "normal_waiting": 30,
        "normal_wait_hours": 18.0,
    },
    "USLAX": {
        "name": "Los Angeles",
        "country": "United States",
        "region": "North America",
        "lat": 33.7327,
        "lon": -118.2580,
        "normal_waiting": 20,
        "normal_wait_hours": 8.0,
    },
    "USLGB": {
        "name": "Long Beach",
        "country": "United States",
        "region": "North America",
        "lat": 33.7565,
        "lon": -118.2205,
        "normal_waiting": 18,
        "normal_wait_hours": 8.0,
    },
    "NLRTM": {
        "name": "Rotterdam",
        "country": "Netherlands",
        "region": "Europe",
        "lat": 51.9036,
        "lon": 4.4925,
        "normal_waiting": 15,
        "normal_wait_hours": 6.0,
    },
    "DEHAM": {
        "name": "Hamburg",
        "country": "Germany",
        "region": "Europe",
        "lat": 53.5325,
        "lon": 9.9323,
        "normal_waiting": 12,
        "normal_wait_hours": 6.0,
    },
    "AEJEA": {
        "name": "Jebel Ali",
        "country": "UAE",
        "region": "Middle East",
        "lat": 24.9857,
        "lon": 55.0272,
        "normal_waiting": 10,
        "normal_wait_hours": 4.0,
    },
    "VNSGN": {
        "name": "Ho Chi Minh City (Cat Lai)",
        "country": "Vietnam",
        "region": "Southeast Asia",
        "lat": 10.7558,
        "lon": 106.7639,
        "normal_waiting": 8,
        "normal_wait_hours": 6.0,
    },
    "VNHPH": {
        "name": "Hai Phong",
        "country": "Vietnam",
        "region": "Southeast Asia",
        "lat": 20.8519,
        "lon": 106.6881,
        "normal_waiting": 5,
        "normal_wait_hours": 4.0,
    },
    "HKHKG": {
        "name": "Hong Kong",
        "country": "Hong Kong",
        "region": "East Asia",
        "lat": 22.2864,
        "lon": 114.1417,
        "normal_waiting": 15,
        "normal_wait_hours": 8.0,
    },
    "KRPUS": {
        "name": "Busan",
        "country": "South Korea",
        "region": "East Asia",
        "lat": 35.0799,
        "lon": 129.0439,
        "normal_waiting": 12,
        "normal_wait_hours": 6.0,
    },
    "BEANR": {
        "name": "Antwerp",
        "country": "Belgium",
        "region": "Europe",
        "lat": 51.2647,
        "lon": 4.3776,
        "normal_waiting": 10,
        "normal_wait_hours": 6.0,
    },
    "USNYC": {
        "name": "New York/New Jersey",
        "country": "United States",
        "region": "North America",
        "lat": 40.6681,
        "lon": -74.0427,
        "normal_waiting": 12,
        "normal_wait_hours": 8.0,
    },
    "CNYTN": {
        "name": "Shenzhen (Yantian)",
        "country": "China",
        "region": "East Asia",
        "lat": 22.5672,
        "lon": 114.2834,
        "normal_waiting": 25,
        "normal_wait_hours": 12.0,
    },
}

# Chokepoint metadata
CHOKEPOINT_METADATA: dict[str, dict] = {
    "Suez Canal": {
        "location": (30.4574, 32.3490),
        "normal_transit_hours": 12.0,
        "daily_transits": 50,
        "affected_routes": ["Asia-Europe", "Asia-Mediterranean"],
    },
    "Panama Canal": {
        "location": (9.0800, -79.6800),
        "normal_transit_hours": 10.0,
        "daily_transits": 35,
        "affected_routes": ["Asia-US East Coast", "Pacific-Atlantic"],
    },
    "Strait of Malacca": {
        "location": (2.5000, 101.5000),
        "normal_transit_hours": 8.0,
        "daily_transits": 80,
        "affected_routes": ["Middle East-Asia", "Europe-Asia"],
    },
    "Strait of Hormuz": {
        "location": (26.5700, 56.2500),
        "normal_transit_hours": 2.0,
        "daily_transits": 20,
        "affected_routes": ["Persian Gulf-Global"],
    },
    "Bab el-Mandeb": {
        "location": (12.5833, 43.3333),
        "normal_transit_hours": 2.0,
        "daily_transits": 30,
        "affected_routes": ["Suez-Indian Ocean", "Red Sea-Gulf of Aden"],
    },
    "Bosphorus": {
        "location": (41.1187, 29.0561),
        "normal_transit_hours": 1.5,
        "daily_transits": 45,
        "affected_routes": ["Black Sea-Mediterranean"],
    },
    "Cape of Good Hope": {
        "location": (-34.3568, 18.4740),
        "normal_transit_hours": 24.0,
        "daily_transits": 30,
        "affected_routes": ["Suez alternative", "South Africa trade"],
    },
}
