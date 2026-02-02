"""
Freight data mapper.

Converts freight rate data to RawSignalEvent.
"""

import hashlib
from datetime import datetime, timezone

from omen.domain.models.raw_signal import RawSignalEvent, MarketMetadata, ProbabilityMovement
from .schemas import FreightRate, FreightIndex, RouteCapacity, RateSpike
from .config import FreightConfig, ROUTE_METADATA


class FreightMapper:
    """Maps freight data to RawSignalEvent."""

    def __init__(self, config: FreightConfig | None = None):
        self.config = config or FreightConfig()

    def map_rate_spike(self, rate: FreightRate) -> RawSignalEvent | None:
        """
        Convert freight rate spike to RawSignalEvent.

        Only creates signal if rate change exceeds threshold.
        """
        # Check if this is a significant rate change
        change_7d = abs(rate.change_7d_pct)
        change_30d = abs(rate.change_30d_pct)

        if (
            change_7d < self.config.min_rate_change_pct
            and change_30d < self.config.min_rate_change_pct
        ):
            return None

        # Use largest change
        change_pct = max(change_7d, change_30d)
        is_increase = rate.change_7d_pct > 0 or rate.change_30d_pct > 0

        # Calculate probability based on spike magnitude
        # 15% → 0.4, 30% → 0.6, 50%+ → 0.9
        probability = min(0.4 + (change_pct - 15) / 50, 0.95)
        probability = max(0.3, probability)

        # Get route metadata
        meta = ROUTE_METADATA.get(rate.route, {})
        origin = meta.get("origin", rate.origin_port)
        destination = meta.get("destination", rate.destination_port)
        region = meta.get("region", "Global")

        # Direction
        direction = "increased" if is_increase else "decreased"

        # Build title
        title = (
            f"Freight Rate {'Spike' if is_increase else 'Drop'}: {rate.route} "
            f"{direction} {change_pct:.0f}% "
            f"(${rate.rate_usd_per_feu:.0f}/FEU)"
        )

        # Build description
        description = (
            f"Container freight rates on route {origin} → {destination} "
            f"{direction} significantly. "
            f"Current rate: ${rate.rate_usd_per_feu:.0f}/FEU. "
        )

        if rate.rate_7d_ago > 0:
            description += (
                f"7-day change: {rate.change_7d_pct:+.1f}% (was ${rate.rate_7d_ago:.0f}). "
            )

        if rate.rate_30d_ago > 0:
            description += (
                f"30-day change: {rate.change_30d_pct:+.1f}% (was ${rate.rate_30d_ago:.0f}). "
            )

        description += f"Capacity utilization: {rate.capacity_utilization_pct:.0f}%. "

        # Add interpretation
        if is_increase and rate.capacity_utilization_pct > 90:
            description += (
                "High rates and utilization indicate capacity shortage and strong demand. "
            )
        elif is_increase:
            description += "Rate increase may signal tightening capacity or increased demand. "
        elif rate.blank_sailings > 0:
            description += f"Rate decrease with {rate.blank_sailings} blank sailings indicates demand weakness. "

        # Keywords
        keywords = [
            "freight_rates",
            (
                "capacity_shortage"
                if is_increase and rate.capacity_utilization_pct > 85
                else "rate_change"
            ),
            rate.origin_code.lower(),
            rate.destination_code.lower(),
            region.lower().replace(" ", "_").replace("-", "_"),
        ]

        if rate.is_spike:
            keywords.append(f"spike_{rate.spike_severity}")

        # Locations
        inferred_locations = [
            origin,
            destination,
            region,
        ]

        # Event ID
        date_str = rate.timestamp.strftime("%Y%m%d")
        event_id = f"freight-rate-{rate.route.lower()}-{date_str}"

        # Note: input_event_hash is computed automatically by RawSignalEvent

        return RawSignalEvent(
            event_id=event_id,
            title=title,
            description=description,
            probability=probability,
            movement=ProbabilityMovement(
                current=probability,
                previous=(
                    max(0.0, probability - 0.15) if is_increase else min(1.0, probability + 0.15)
                ),
                delta=min(change_pct / 100, 0.5) if is_increase else max(-change_pct / 100, -0.5),
                window_hours=168 if change_7d > change_30d else 720,
            ),
            keywords=keywords,
            market=MarketMetadata(
                source="freight",
                market_id=rate.route,
                total_volume_usd=0.0,
                current_liquidity_usd=0.0,
                created_at=rate.timestamp,
            ),
            source_metrics={
                "route": rate.route,
                "rate_usd_per_feu": rate.rate_usd_per_feu,
                "change_7d_pct": rate.change_7d_pct,
                "change_30d_pct": rate.change_30d_pct,
                "capacity_utilization_pct": rate.capacity_utilization_pct,
                "booking_volume_index": rate.booking_volume_index,
                "blank_sailings": rate.blank_sailings,
                "is_spike": rate.is_spike,
                "spike_severity": rate.spike_severity,
                "is_increase": is_increase,
                "locations": inferred_locations,
            },
        )

    def map_index_change(self, index: FreightIndex) -> RawSignalEvent | None:
        """Convert freight index change to RawSignalEvent."""
        change_7d = abs(index.change_7d_pct)

        if change_7d < 10:  # Need significant index move
            return None

        is_increase = index.change_7d_pct > 0
        probability = min(0.5 + (change_7d - 10) / 40, 0.9)

        title = (
            f"Freight Index Alert: {index.index_name} "
            f"{'up' if is_increase else 'down'} {change_7d:.0f}% "
            f"({index.index_value:.0f})"
        )

        description = (
            f"Global freight index {index.index_name} "
            f"{'increased' if is_increase else 'decreased'} {change_7d:.1f}% this week. "
            f"Current value: {index.index_value:.0f}. "
            f"30-day change: {index.change_30d_pct:+.1f}%. "
            f"YTD change: {index.change_ytd_pct:+.1f}%. "
            f"52-week range: {index.value_52w_low:.0f} - {index.value_52w_high:.0f}."
        )

        event_id = f"freight-index-{index.index_name.lower()}-{index.timestamp.strftime('%Y%m%d')}"

        # Note: input_event_hash is computed automatically by RawSignalEvent

        return RawSignalEvent(
            event_id=event_id,
            title=title,
            description=description,
            probability=probability,
            keywords=["freight_index", index.index_name.lower(), "market_indicator"],
            market=MarketMetadata(
                source="freight",
                market_id=f"index-{index.index_name}",
                total_volume_usd=0.0,
                current_liquidity_usd=0.0,
                created_at=index.timestamp,
            ),
            source_metrics={
                "index_name": index.index_name,
                "index_value": index.index_value,
                "change_7d_pct": index.change_7d_pct,
                "change_30d_pct": index.change_30d_pct,
                "locations": ["Global"],
            },
        )

    def map_capacity_alert(self, capacity: RouteCapacity) -> RawSignalEvent | None:
        """Convert capacity shortage/oversupply to RawSignalEvent."""
        if capacity.capacity_outlook == "balanced":
            return None

        # Map outlook to probability
        outlook_prob = {
            "oversupply": 0.4,
            "tight": 0.6,
            "severe_shortage": 0.85,
        }
        probability = outlook_prob.get(capacity.capacity_outlook, 0.5)

        meta = ROUTE_METADATA.get(capacity.route, {})

        title = (
            f"Capacity Alert: {capacity.route} - "
            f"{capacity.capacity_outlook.replace('_', ' ').title()} "
            f"({capacity.utilization_pct:.0f}% utilized)"
        )

        description = (
            f"Capacity outlook for {capacity.route}: {capacity.capacity_outlook.replace('_', ' ')}. "
            f"Utilization: {capacity.utilization_pct:.0f}%. "
            f"Scheduled sailings: {capacity.scheduled_sailings}, "
            f"blank sailings: {capacity.blank_sailings}. "
            f"Rollover rate: {capacity.rollover_rate_pct:.1f}%."
        )

        event_id = (
            f"freight-capacity-{capacity.route.lower()}-{capacity.timestamp.strftime('%Y%m%d')}"
        )

        return RawSignalEvent(
            event_id=event_id,
            title=title,
            description=description,
            probability=probability,
            keywords=[
                "capacity_" + capacity.capacity_outlook,
                capacity.route.lower().replace("-", "_"),
            ],
            market=MarketMetadata(
                source="freight",
                market_id=f"capacity-{capacity.route}",
                total_volume_usd=0.0,
                current_liquidity_usd=0.0,
                created_at=capacity.timestamp,
            ),
            source_metrics={
                "route": capacity.route,
                "utilization_pct": capacity.utilization_pct,
                "capacity_outlook": capacity.capacity_outlook,
                "blank_sailings": capacity.blank_sailings,
                "locations": [meta.get("origin", ""), meta.get("destination", "")],
            },
        )
