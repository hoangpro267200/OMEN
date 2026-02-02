"""
AIS data mapper.

Converts AIS data (port status, chokepoint status) to RawSignalEvent.
"""

import hashlib
from datetime import datetime, timezone

from omen.domain.models.raw_signal import RawSignalEvent, MarketMetadata, ProbabilityMovement
from .schemas import PortStatus, ChokePointStatus, PortCongestionAlert, ChokePointAlert
from .config import AISConfig, PORT_METADATA, CHOKEPOINT_METADATA


class AISMapper:
    """Maps AIS data to RawSignalEvent."""

    # Average cargo value per vessel (conservative estimate)
    AVG_CARGO_VALUE_PER_VESSEL = 50_000_000.0  # $50M per container ship

    def __init__(self, config: AISConfig | None = None):
        self.config = config or AISConfig()

    def map_port_congestion(self, port_status: PortStatus) -> RawSignalEvent | None:
        """
        Convert port congestion to RawSignalEvent.

        Only creates signal if anomaly is detected (congestion_ratio > threshold).
        """
        if not port_status.anomaly_detected:
            return None

        congestion_ratio = port_status.congestion_ratio

        # Calculate probability: 150% → 0.5, 300% → 1.0
        # Formula: min((ratio - 1.0) / 2.0, 1.0)
        probability = min((congestion_ratio - 1.0) / 2.0, 1.0)
        probability = max(0.0, probability)  # Clamp to [0, 1]

        # Build title
        change_pct = (congestion_ratio - 1.0) * 100
        title = (
            f"Port Congestion Alert: {port_status.port_name} "
            f"({port_status.vessels_waiting} vessels waiting, ↑{change_pct:.0f}%)"
        )

        # Build description
        wait_time_change = (
            (port_status.avg_wait_time_hours / port_status.normal_wait_time_hours - 1) * 100
            if port_status.normal_wait_time_hours > 0
            else 0
        )
        description = (
            f"Container port congestion detected at {port_status.port_name} "
            f"({port_status.country}). "
            f"Current: {port_status.vessels_waiting} vessels waiting to berth "
            f"(normal: {port_status.normal_waiting}). "
            f"Average wait time: {port_status.avg_wait_time_hours:.1f} hours "
            f"(↑{wait_time_change:.0f}%). "
            f"Congestion ratio: {congestion_ratio:.1f}x normal. "
            f"Affects: Regional supply chain, import/export delays."
        )

        # Extract keywords
        keywords = [
            "port_congestion",
            port_status.country.lower().replace(" ", "_"),
            port_status.port_name.lower().replace(" ", "_"),
            "container_shipping",
            "supply_chain_disruption",
            f"severity_{port_status.anomaly_severity}",
        ]

        # Infer affected locations
        inferred_locations = [port_status.port_name, port_status.country]
        if port_status.region:
            inferred_locations.append(port_status.region)

        # Build event_id (deterministic)
        event_id = f"ais-port-{port_status.port_code}-{port_status.timestamp.strftime('%Y%m%d%H')}"

        # Note: input_event_hash is computed automatically by RawSignalEvent

        # Build MarketMetadata
        market = MarketMetadata(
            source="ais",
            market_id=port_status.port_code,
            total_volume_usd=self._estimate_cargo_value(port_status.vessels_waiting),
            current_liquidity_usd=0.0,  # N/A for AIS
            created_at=port_status.timestamp,
        )

        # Build RawSignalEvent
        return RawSignalEvent(
            event_id=event_id,
            title=title,
            description=description,
            probability=probability,
            movement=ProbabilityMovement(
                current=probability,
                previous=max(0.0, probability - 0.1),
                delta=0.1 if congestion_ratio > 1.5 else 0.0,
                window_hours=24,
            ),
            keywords=keywords,
            market=market,
            source_metrics={
                "vessels_waiting": port_status.vessels_waiting,
                "vessels_berthed": port_status.vessels_berthed,
                "avg_wait_time_hours": port_status.avg_wait_time_hours,
                "congestion_ratio": congestion_ratio,
                "wait_time_ratio": port_status.wait_time_ratio,
                "normal_waiting": port_status.normal_waiting,
                "port_code": port_status.port_code,
                "anomaly_severity": port_status.anomaly_severity,
                "data_quality": port_status.data_quality,
                "locations": inferred_locations,  # Store locations here instead
            },
        )

    def map_chokepoint_delay(self, chokepoint: ChokePointStatus) -> RawSignalEvent | None:
        """
        Convert chokepoint delay to RawSignalEvent.

        Only creates signal if delays are detected.
        """
        if not chokepoint.delays_detected and not chokepoint.blockage_detected:
            return None

        delay_ratio = chokepoint.delay_ratio

        # Probability based on delay severity
        # 1.5x delay → 0.5, 2x+ delay → 1.0
        if chokepoint.blockage_detected:
            probability = 1.0
        else:
            probability = min((delay_ratio - 1.0) / 1.0, 1.0)
            probability = max(0.0, probability)

        # Build title
        if chokepoint.blockage_detected:
            title = (
                f"CRITICAL: {chokepoint.name} Blockage "
                f"({chokepoint.vessels_waiting} vessels waiting)"
            )
        else:
            delay_hours = chokepoint.avg_transit_time_hours - chokepoint.normal_transit_time_hours
            title = (
                f"Chokepoint Delay: {chokepoint.name} "
                f"(+{delay_hours:.0f}h transit time, {chokepoint.vessels_waiting} vessels queued)"
            )

        # Build description
        delay_hours = chokepoint.avg_transit_time_hours - chokepoint.normal_transit_time_hours
        description = (
            f"{'BLOCKAGE' if chokepoint.blockage_detected else 'Delays'} detected at {chokepoint.name}. "
            f"Transit time: {chokepoint.avg_transit_time_hours:.1f}h "
            f"(normal: {chokepoint.normal_transit_time_hours:.1f}h, +{delay_hours:.1f}h). "
            f"{chokepoint.vessels_waiting} vessels waiting to transit. "
            f"Affected routes: {', '.join(chokepoint.affected_routes) or 'Multiple global routes'}. "
            f"This affects major global shipping and supply chains."
        )

        # Keywords
        chokepoint_key = chokepoint.name.lower().replace(" ", "_")
        keywords = [
            "chokepoint_delay" if not chokepoint.blockage_detected else "chokepoint_blockage",
            chokepoint_key,
            "global_shipping",
            "supply_chain_disruption",
            f"severity_{chokepoint.queue_severity}",
        ]

        # Inferred locations
        inferred_locations = [chokepoint.name] + chokepoint.affected_routes

        # Event ID
        event_id = f"ais-chokepoint-{chokepoint_key}-{chokepoint.timestamp.strftime('%Y%m%d%H')}"

        # Note: input_event_hash is computed automatically by RawSignalEvent

        # Market metadata
        market = MarketMetadata(
            source="ais",
            market_id=f"chokepoint-{chokepoint_key}",
            total_volume_usd=self._estimate_cargo_value(
                chokepoint.vessels_waiting + chokepoint.vessels_in_transit
            ),
            current_liquidity_usd=0.0,
            created_at=chokepoint.timestamp,
        )

        return RawSignalEvent(
            event_id=event_id,
            title=title,
            description=description,
            probability=probability,
            movement=ProbabilityMovement(
                current=probability,
                previous=max(0.0, probability - 0.15),
                delta=0.15 if chokepoint.delays_detected else 0.0,
                window_hours=24,
            ),
            keywords=keywords,
            market=market,
            source_metrics={
                "vessels_waiting": chokepoint.vessels_waiting,
                "vessels_in_transit": chokepoint.vessels_in_transit,
                "avg_transit_time_hours": chokepoint.avg_transit_time_hours,
                "normal_transit_time_hours": chokepoint.normal_transit_time_hours,
                "delay_ratio": delay_ratio,
                "delay_hours": delay_hours,
                "blockage_detected": chokepoint.blockage_detected,
                "queue_severity": chokepoint.queue_severity,
                "affected_routes": chokepoint.affected_routes,
                "locations": inferred_locations,
            },
        )

    def map_port_alert(self, alert: PortCongestionAlert) -> RawSignalEvent:
        """Map pre-computed port alert to RawSignalEvent."""
        # Similar to map_port_congestion but from alert object
        severity_to_prob = {
            "low": 0.4,
            "medium": 0.6,
            "high": 0.8,
            "critical": 0.95,
        }
        probability = severity_to_prob.get(alert.severity, 0.5)

        title = (
            f"Port Congestion Alert [{alert.severity.upper()}]: {alert.port_name} "
            f"({alert.vessels_waiting} vessels, {alert.congestion_ratio:.1f}x normal)"
        )

        return RawSignalEvent(
            event_id=alert.alert_id,
            title=title,
            description=f"Port congestion at {alert.port_name}: {alert.vessels_waiting} vessels waiting. "
            f"Average wait time: {alert.wait_time_hours:.1f}h. "
            f"Estimated cargo value affected: ${alert.estimated_cargo_value_usd/1e6:.0f}M.",
            probability=probability,
            keywords=["port_congestion", alert.port_code.lower(), f"severity_{alert.severity}"],
            market=MarketMetadata(
                source="ais",
                market_id=alert.port_code,
                total_volume_usd=alert.estimated_cargo_value_usd,
                current_liquidity_usd=0.0,
                created_at=alert.data_timestamp,
            ),
            source_metrics={
                "vessels_waiting": alert.vessels_waiting,
                "congestion_ratio": alert.congestion_ratio,
                "wait_time_hours": alert.wait_time_hours,
                "severity": alert.severity,
                "locations": [alert.port_name],
            },
        )

    def map_chokepoint_alert(self, alert: ChokePointAlert) -> RawSignalEvent:
        """Map pre-computed chokepoint alert to RawSignalEvent."""
        severity_to_prob = {
            "low": 0.4,
            "medium": 0.6,
            "high": 0.8,
            "critical": 0.95,
        }
        probability = severity_to_prob.get(alert.severity, 0.5)

        chokepoint_key = alert.chokepoint_name.lower().replace(" ", "_")
        title = (
            f"Chokepoint Alert [{alert.severity.upper()}]: {alert.chokepoint_name} "
            f"({alert.alert_type}, +{alert.delay_hours:.0f}h delay)"
        )

        return RawSignalEvent(
            event_id=alert.alert_id,
            title=title,
            description=f"{alert.alert_type.title()} at {alert.chokepoint_name}: "
            f"{alert.vessels_waiting} vessels waiting, +{alert.delay_hours:.1f}h delay. "
            f"Affected routes: {', '.join(alert.affected_routes)}.",
            probability=probability,
            keywords=[
                "chokepoint_" + alert.alert_type,
                chokepoint_key,
                f"severity_{alert.severity}",
            ],
            market=MarketMetadata(
                source="ais",
                market_id=f"chokepoint-{chokepoint_key}",
                total_volume_usd=self._estimate_cargo_value(alert.estimated_vessels_affected),
                current_liquidity_usd=0.0,
                created_at=alert.data_timestamp,
            ),
            source_metrics={
                "vessels_waiting": alert.vessels_waiting,
                "delay_hours": alert.delay_hours,
                "delay_ratio": alert.delay_ratio,
                "alert_type": alert.alert_type,
                "severity": alert.severity,
                "affected_routes": alert.affected_routes,
                "locations": [alert.chokepoint_name] + alert.affected_routes,
            },
        )

    def _estimate_cargo_value(self, vessel_count: int) -> float:
        """Estimate total cargo value for a number of vessels."""
        return vessel_count * self.AVG_CARGO_VALUE_PER_VESSEL

    @staticmethod
    def _get_region(country: str) -> str | None:
        """Map country to region."""
        regions = {
            "Vietnam": "Southeast Asia",
            "Singapore": "Southeast Asia",
            "China": "East Asia",
            "Hong Kong": "East Asia",
            "South Korea": "East Asia",
            "Japan": "East Asia",
            "United States": "North America",
            "Netherlands": "Europe",
            "Germany": "Europe",
            "Belgium": "Europe",
            "UAE": "Middle East",
            "Saudi Arabia": "Middle East",
        }
        return regions.get(country)
