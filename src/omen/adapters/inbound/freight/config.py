"""
Freight rates adapter configuration.
"""

from typing import Literal
from pydantic import BaseModel, Field


class FreightConfig(BaseModel):
    """Freight rates adapter configuration."""

    # Provider selection
    provider: Literal["freightos", "drewry", "xeneta", "mock"] = Field(
        default="mock",
        description="Freight data provider",
    )

    # Freightos (FBX index)
    freightos_api_key: str | None = Field(default=None)
    freightos_base_url: str = Field(default="https://api.freightos.com/v1")

    # Drewry (WCI index)
    drewry_api_key: str | None = Field(default=None)

    # Xeneta
    xeneta_api_key: str | None = Field(default=None)

    # Monitored routes
    monitored_routes: list[str] = Field(
        default=[
            "SHA-LAX",  # Shanghai to Los Angeles
            "SHA-RTM",  # Shanghai to Rotterdam
            "SHA-NYC",  # Shanghai to New York
            "NGB-LAX",  # Ningbo to Los Angeles
            "SIN-RTM",  # Singapore to Rotterdam
            "HKG-LAX",  # Hong Kong to Los Angeles
            "YTN-LAX",  # Yantian to Los Angeles
            "PUS-LAX",  # Busan to Los Angeles
        ],
        description="Trade routes to monitor",
    )

    # Spike detection thresholds
    min_rate_change_pct: float = Field(
        default=15.0,
        description="Minimum rate change % to trigger alert",
    )
    spike_threshold_pct: float = Field(
        default=25.0,
        description="Rate change % considered a spike",
    )

    # Time windows
    short_term_days: int = Field(default=7, description="Short-term comparison window")
    medium_term_days: int = Field(default=30, description="Medium-term comparison window")

    # Update frequency
    polling_interval_seconds: int = Field(
        default=3600,
        description="Polling interval (1 hour default)",
    )

    class Config:
        env_prefix = "OMEN_FREIGHT_"


# Route metadata
ROUTE_METADATA = {
    "SHA-LAX": {
        "origin": "Shanghai",
        "origin_code": "CNSHA",
        "destination": "Los Angeles",
        "destination_code": "USLAX",
        "region": "Trans-Pacific",
        "distance_nm": 6500,
        "transit_days": 14,
        "baseline_rate_usd": 2000,  # FEU baseline (historical)
    },
    "SHA-RTM": {
        "origin": "Shanghai",
        "origin_code": "CNSHA",
        "destination": "Rotterdam",
        "destination_code": "NLRTM",
        "region": "Asia-Europe",
        "distance_nm": 10500,
        "transit_days": 28,
        "baseline_rate_usd": 1500,
    },
    "SHA-NYC": {
        "origin": "Shanghai",
        "origin_code": "CNSHA",
        "destination": "New York",
        "destination_code": "USNYC",
        "region": "Trans-Pacific East",
        "distance_nm": 11500,
        "transit_days": 35,
        "baseline_rate_usd": 2500,
    },
    "NGB-LAX": {
        "origin": "Ningbo",
        "origin_code": "CNNGB",
        "destination": "Los Angeles",
        "destination_code": "USLAX",
        "region": "Trans-Pacific",
        "distance_nm": 6400,
        "transit_days": 14,
        "baseline_rate_usd": 1900,
    },
    "SIN-RTM": {
        "origin": "Singapore",
        "origin_code": "SGSIN",
        "destination": "Rotterdam",
        "destination_code": "NLRTM",
        "region": "Asia-Europe",
        "distance_nm": 8400,
        "transit_days": 21,
        "baseline_rate_usd": 1400,
    },
    "HKG-LAX": {
        "origin": "Hong Kong",
        "origin_code": "HKHKG",
        "destination": "Los Angeles",
        "destination_code": "USLAX",
        "region": "Trans-Pacific",
        "distance_nm": 6800,
        "transit_days": 15,
        "baseline_rate_usd": 2100,
    },
    "YTN-LAX": {
        "origin": "Yantian",
        "origin_code": "CNYTN",
        "destination": "Los Angeles",
        "destination_code": "USLAX",
        "region": "Trans-Pacific",
        "distance_nm": 6700,
        "transit_days": 14,
        "baseline_rate_usd": 2000,
    },
    "PUS-LAX": {
        "origin": "Busan",
        "origin_code": "KRPUS",
        "destination": "Los Angeles",
        "destination_code": "USLAX",
        "region": "Trans-Pacific",
        "distance_nm": 5800,
        "transit_days": 12,
        "baseline_rate_usd": 1800,
    },
}
