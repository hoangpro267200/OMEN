"""
Weather data mapper.

Converts weather alerts to RawSignalEvent.
"""

import hashlib
from datetime import datetime, timezone

from omen.domain.models.raw_signal import RawSignalEvent, MarketMetadata, ProbabilityMovement
from .schemas import StormAlert, WeatherWarning, SeaConditions
from .config import WeatherConfig, SHIPPING_LANES


class WeatherMapper:
    """Maps weather data to RawSignalEvent."""

    AVG_CARGO_VALUE_PER_VESSEL = 50_000_000.0

    def __init__(self, config: WeatherConfig | None = None):
        self.config = config or WeatherConfig()

    def map_storm_alert(self, storm: StormAlert) -> RawSignalEvent | None:
        """
        Convert storm alert to RawSignalEvent.

        Only creates signal if storm meets severity threshold.
        """
        if storm.category < self.config.min_storm_category:
            return None

        # Calculate probability based on category and confidence
        category_score = min(storm.category / 5.0, 1.0)
        probability = (category_score * 0.7 + storm.path_confidence * 0.3)
        probability = max(0.0, min(1.0, probability))

        # Storm type name
        storm_type_name = {
            "tropical_storm": "Tropical Storm",
            "hurricane": "Hurricane",
            "typhoon": "Typhoon",
            "cyclone": "Cyclone",
        }.get(storm.storm_type, "Storm")

        # Build title
        title = (
            f"{storm_type_name} Alert: {storm.name} (Category {storm.category}) "
            f"approaching {', '.join(storm.affected_ports[:2]) or 'shipping lanes'}"
        )

        # Build description
        description = (
            f"{storm_type_name} {storm.name} intensified to Category {storm.category} "
            f"with sustained winds of {storm.wind_speed_kts} knots "
            f"({storm.wind_speed_mph or int(storm.wind_speed_kts * 1.151)} mph). "
            f"Central pressure: {storm.pressure_mb} mb. "
        )

        if storm.affected_shipping_lanes:
            description += f"Forecast path crosses shipping lanes: {', '.join(storm.affected_shipping_lanes)}. "

        if storm.affected_ports:
            description += f"Potentially affected ports: {', '.join(storm.affected_ports)}. "

        if storm.estimated_vessels_at_risk > 0:
            description += f"Estimated {storm.estimated_vessels_at_risk} vessels may need to re-route. "

        description += f"Forecast confidence: {storm.path_confidence:.0%}."

        # Keywords
        keywords = [
            storm.storm_type,
            "severe_weather",
            "shipping_disruption",
            f"category_{storm.category}",
        ]
        keywords.extend([p.lower().replace(" ", "_") for p in storm.affected_ports[:3]])

        # Locations
        inferred_locations = list(storm.affected_ports) + list(storm.affected_shipping_lanes)

        # Event ID
        date_str = storm.timestamp.strftime("%Y%m%d")
        event_id = f"weather-storm-{storm.storm_id}-{date_str}"

        # Note: input_event_hash is computed automatically by RawSignalEvent

        return RawSignalEvent(
            event_id=event_id,
            title=title,
            description=description,
            probability=probability,
            movement=ProbabilityMovement(
                current=probability,
                previous=max(0.0, probability - 0.2),
                delta=min(storm.category / 5.0, 0.5),
                window_hours=72,
            ),
            keywords=keywords,
            market=MarketMetadata(
                source="weather",
                market_id=storm.storm_id,
                total_volume_usd=storm.estimated_vessels_at_risk * self.AVG_CARGO_VALUE_PER_VESSEL,
                current_liquidity_usd=0.0,
                created_at=storm.timestamp,
            ),
            source_metrics={
                "storm_id": storm.storm_id,
                "storm_name": storm.name,
                "storm_type": storm.storm_type,
                "storm_category": storm.category,
                "wind_speed_kts": storm.wind_speed_kts,
                "pressure_mb": storm.pressure_mb,
                "path_confidence": storm.path_confidence,
                "vessels_at_risk": storm.estimated_vessels_at_risk,
                "affected_ports": storm.affected_ports,
                "affected_lanes": storm.affected_shipping_lanes,
                "locations": inferred_locations,
            },
        )

    def map_weather_warning(self, warning: WeatherWarning) -> RawSignalEvent | None:
        """Convert weather warning to RawSignalEvent."""
        # Severity to probability
        severity_prob = {
            "advisory": 0.3,
            "watch": 0.5,
            "warning": 0.7,
            "emergency": 0.9,
        }
        probability = severity_prob.get(warning.severity, 0.5)

        title = f"Weather Warning [{warning.severity.upper()}]: {warning.headline}"

        description = warning.description or (
            f"{warning.warning_type.title()} {warning.severity} issued for {warning.region}. "
            f"Valid from {warning.start_time.strftime('%Y-%m-%d %H:%M')} UTC."
        )

        if warning.affected_ports:
            description += f" Affected ports: {', '.join(warning.affected_ports)}."

        keywords = [
            "weather_warning",
            warning.warning_type,
            warning.severity,
            warning.region.lower().replace(" ", "_"),
        ]

        locations = [warning.region] + warning.affected_ports + warning.affected_routes

        event_id = f"weather-warning-{warning.warning_id}"

        # Note: input_event_hash is computed automatically by RawSignalEvent

        return RawSignalEvent(
            event_id=event_id,
            title=title,
            description=description,
            probability=probability,
            keywords=keywords,
            market=MarketMetadata(
                source="weather",
                market_id=warning.warning_id,
                total_volume_usd=0.0,
                current_liquidity_usd=0.0,
                created_at=warning.timestamp,
            ),
            source_metrics={
                "warning_id": warning.warning_id,
                "warning_type": warning.warning_type,
                "severity": warning.severity,
                "region": warning.region,
                "locations": locations,
            },
        )

    def map_sea_conditions(self, conditions: SeaConditions) -> RawSignalEvent | None:
        """
        Convert severe sea conditions to RawSignalEvent.

        Only creates signal for rough or worse conditions.
        """
        if conditions.conditions in ["calm", "moderate"]:
            return None

        # Map conditions to probability
        conditions_prob = {
            "rough": 0.5,
            "very_rough": 0.7,
            "high": 0.85,
            "phenomenal": 0.95,
        }
        probability = conditions_prob.get(conditions.conditions, 0.5)

        title = (
            f"Sea Conditions Alert: {conditions.region} "
            f"({conditions.conditions.replace('_', ' ').title()}, "
            f"{conditions.wave_height_m:.1f}m waves)"
        )

        description = (
            f"Severe sea conditions in {conditions.region}. "
            f"Wave height: {conditions.wave_height_m:.1f}m. "
            f"Wind: {conditions.wind_speed_kts:.0f} kts. "
            f"Sea state: {conditions.sea_state}/9 (Douglas scale). "
            f"Visibility: {conditions.visibility_nm:.0f} nm. "
        )

        if conditions.navigation_advisory:
            description += conditions.navigation_advisory

        keywords = [
            "sea_conditions",
            conditions.conditions,
            conditions.region.lower().replace(" ", "_"),
        ]

        event_id = f"weather-sea-{conditions.region.lower().replace(' ', '_')}-{conditions.timestamp.strftime('%Y%m%d%H')}"

        # Note: input_event_hash is computed automatically by RawSignalEvent

        return RawSignalEvent(
            event_id=event_id,
            title=title,
            description=description,
            probability=probability,
            keywords=keywords,
            market=MarketMetadata(
                source="weather",
                market_id=f"sea-{conditions.region.lower().replace(' ', '_')}",
                total_volume_usd=0.0,
                current_liquidity_usd=0.0,
                created_at=conditions.timestamp,
            ),
            source_metrics={
                "region": conditions.region,
                "wave_height_m": conditions.wave_height_m,
                "wind_speed_kts": conditions.wind_speed_kts,
                "sea_state": conditions.sea_state,
                "conditions": conditions.conditions,
                "locations": [conditions.region],
            },
        )
