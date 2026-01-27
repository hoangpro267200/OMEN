"""
Evidence-based parameters for logistics impact rules.

All constants are documented with sources and update dates.
This file should be reviewed and updated quarterly.
"""

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class EvidenceRecord:
    """Documentation for a parameter value."""

    value: float
    unit: str
    source: str
    source_date: date
    notes: str | None = None


# === RED SEA / SUEZ CANAL PARAMETERS ===

RED_SEA_PARAMS: dict[str, EvidenceRecord] = {
    "reroute_distance_increase_nm": EvidenceRecord(
        value=3000,
        unit="nautical_miles",
        source="Clarksons Research, 2024 Red Sea Crisis Analysis",
        source_date=date(2024, 1, 15),
        notes="Asia-Europe via Cape vs Suez. Actual range: 2800-3400nm depending on origin.",
    ),
    "reroute_transit_increase_days": EvidenceRecord(
        value=10,
        unit="days",
        source="Drewry Maritime Research Q1 2024",
        source_date=date(2024, 2, 1),
        notes="Average for container vessels. Range: 7-14 days based on vessel speed and port.",
    ),
    "fuel_consumption_increase_pct": EvidenceRecord(
        value=30,
        unit="percent",
        source="Lloyd's List Intelligence, Jan 2024",
        source_date=date(2024, 1, 20),
        notes="Based on bunker consumption for extended voyage. Assumes similar speed.",
    ),
    "freight_rate_increase_pct_base": EvidenceRecord(
        value=15,
        unit="percent",
        source="Freightos Baltic Index historical analysis",
        source_date=date(2024, 1, 25),
        notes="Minimum observed increase. Actual spikes reached 200%+ in crisis periods.",
    ),
    "freight_rate_increase_pct_crisis": EvidenceRecord(
        value=100,
        unit="percent",
        source="Freightos Baltic Index, Dec 2023-Jan 2024",
        source_date=date(2024, 1, 30),
        notes="Peak rates during Houthi attacks. Used for high-probability scenarios.",
    ),
    "insurance_premium_increase_pct": EvidenceRecord(
        value=50,
        unit="percent",
        source="Lloyd's of London War Risk Premium updates",
        source_date=date(2024, 1, 18),
        notes="War risk premium for Red Sea transit. Can reach 1% of hull value.",
    ),
}


# === PORT CLOSURE PARAMETERS ===

PORT_CLOSURE_PARAMS: dict[str, EvidenceRecord] = {
    "major_port_daily_capacity_teu": EvidenceRecord(
        value=50000,
        unit="TEU/day",
        source="UNCTAD Port Statistics 2023",
        source_date=date(2023, 12, 1),
        notes="Average for top 20 global ports. Range: 20k-100k TEU/day.",
    ),
    "congestion_buildup_rate": EvidenceRecord(
        value=1.5,
        unit="days_delay_per_closure_day",
        source="Journal of Maritime Economics, 2022",
        source_date=date(2022, 6, 15),
        notes="Empirical analysis of port closure aftereffects.",
    ),
    "diversion_cost_increase_pct": EvidenceRecord(
        value=25,
        unit="percent",
        source="Sea-Intelligence Sunday Spotlight",
        source_date=date(2023, 9, 10),
        notes="Cost increase for diverting to alternative ports.",
    ),
}


# === STRIKE / LABOR DISRUPTION PARAMETERS ===

STRIKE_PARAMS: dict[str, EvidenceRecord] = {
    "port_strike_productivity_loss_pct": EvidenceRecord(
        value=60,
        unit="percent",
        source="International Longshore and Warehouse Union historical data",
        source_date=date(2023, 8, 1),
        notes="Average productivity loss during strike. Range: 30-100%.",
    ),
    "truck_strike_capacity_loss_pct": EvidenceRecord(
        value=40,
        unit="percent",
        source="American Trucking Associations, 2022 analysis",
        source_date=date(2022, 11, 1),
        notes="Estimated capacity loss during major trucking strikes.",
    ),
    "strike_duration_avg_days": EvidenceRecord(
        value=7,
        unit="days",
        source="Bureau of Labor Statistics Work Stoppages data",
        source_date=date(2023, 12, 31),
        notes="Median duration of work stoppages in transportation sector.",
    ),
}


def get_param(params: dict[str, EvidenceRecord], key: str) -> tuple[float, str]:
    """Get parameter value and source citation."""
    record = params[key]
    return record.value, f"{record.source} ({record.source_date})"
