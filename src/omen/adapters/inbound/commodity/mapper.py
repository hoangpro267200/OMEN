"""
Commodity Spike to RawSignalEvent Mapper.

Converts detected commodity spikes to RawSignalEvent format.
Maintains determinism through stable hashing.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone

from omen.domain.models.raw_signal import RawSignalEvent, MarketMetadata
from omen.domain.models.common import ProbabilityMovement

from .config import CommodityConfig
from .schemas import CommoditySpike


class CommodityMapper:
    """
    Maps commodity spikes to RawSignalEvent.

    Key principles:
    - Only spikes are mapped (not routine price changes)
    - Deterministic output
    - Commodity signals are context, not primary risk indicators
    """

    def __init__(self, config: CommodityConfig | None = None):
        self._config = config or CommodityConfig()
        self._category_weights = self._config.get_category_weights()

    def map_spike(
        self,
        spike: CommoditySpike,
        asof_ts: datetime | None = None,
    ) -> RawSignalEvent | None:
        """
        Map a commodity spike to RawSignalEvent.

        Args:
            spike: Detected commodity spike
            asof_ts: Reference timestamp for observed_at

        Returns:
            RawSignalEvent or None if not a spike
        """
        if not spike.is_spike:
            return None

        # Use asof_ts for determinism
        observed_at = asof_ts or datetime.now(timezone.utc)
        if observed_at.tzinfo is None:
            observed_at = observed_at.replace(tzinfo=timezone.utc)

        # Generate deterministic event_id
        event_id = self._generate_event_id(spike)

        # Build title
        title = self._build_title(spike)

        # Build description
        description = self._build_description(spike)

        # Calculate probability
        probability = self._calculate_probability(spike)

        # Build keywords
        keywords = self._build_keywords(spike)

        # Build market metadata
        market = MarketMetadata(
            source="commodity",
            market_id=f"{spike.symbol}-{spike.price_timestamp.strftime('%Y%m%d')}",
            total_volume_usd=0.0,  # N/A
            current_liquidity_usd=0.0,  # N/A
            created_at=spike.price_timestamp,
        )

        # Movement
        movement = ProbabilityMovement(
            current=probability,
            previous=0.5,
            delta=probability - 0.5,
            window_hours=168,  # 7 days
        )

        return RawSignalEvent(
            event_id=event_id,
            title=title,
            description=description,
            probability=probability,
            movement=movement,
            keywords=keywords,
            market=market,
            observed_at=observed_at,
            source_metrics=spike.to_source_metrics(),
        )

    def _generate_event_id(self, spike: CommoditySpike) -> str:
        """Generate deterministic event ID."""
        date_str = spike.price_timestamp.strftime("%Y%m%d")

        hash_input = f"{spike.symbol}|{spike.direction}|{date_str}|{spike.severity}"
        short_hash = hashlib.sha256(hash_input.encode()).hexdigest()[:8]

        return f"commodity-{spike.symbol.lower()}-{spike.direction}-{date_str}-{short_hash}"

    def _build_title(self, spike: CommoditySpike) -> str:
        """Build signal title."""
        direction_word = "Surge" if spike.direction == "up" else "Drop"
        severity_word = spike.severity.title()

        return (
            f"Commodity Alert [{severity_word}]: {spike.name} {direction_word} "
            f"{abs(spike.pct_change):.1f}% (${spike.current_price:.2f})"
        )

    def _build_description(self, spike: CommoditySpike) -> str:
        """Build signal description."""
        parts = [
            f"{spike.name} ({spike.symbol}) experienced a {spike.severity} "
            f"{'increase' if spike.direction == 'up' else 'decrease'}.",
            f"Current price: ${spike.current_price:.2f}",
            f"Change from {spike.baseline_period_days}-day baseline: {spike.pct_change:+.1f}%",
            f"Z-score: {spike.zscore:.2f}",
        ]

        if spike.impact_hint:
            parts.append(f"Potential impact: {spike.impact_hint}")

        return " | ".join(parts)

    def _calculate_probability(self, spike: CommoditySpike) -> float:
        """
        Calculate probability based on spike characteristics.

        Higher probability = higher likelihood of impact on logistics.

        Factors:
        - Severity (minor/moderate/major)
        - Category weight (energy > metals > agricultural)
        - Z-score magnitude
        """
        # Base probability by severity
        severity_base = {
            "minor": 0.45,
            "moderate": 0.60,
            "major": 0.75,
        }
        base = severity_base.get(spike.severity, 0.50)

        # Category weight
        category_weight = self._category_weights.get(spike.category, 0.5)

        # Z-score contribution (0 to 0.15)
        zscore_contrib = min(abs(spike.zscore) / 5.0, 1.0) * 0.15

        # Calculate final probability
        probability = base + zscore_contrib
        probability *= category_weight

        # Clamp to valid range
        return max(0.30, min(0.90, probability))

    def _build_keywords(self, spike: CommoditySpike) -> list[str]:
        """Build keyword list."""
        keywords = {
            "commodity",
            spike.symbol.lower(),
            spike.category.lower(),
            f"spike_{spike.severity}",
            spike.direction,
        }

        # Add category-specific keywords
        if spike.category == "energy":
            keywords.update(["energy", "fuel", "oil"])
        elif spike.category == "metals":
            keywords.update(["metals", "industrial"])

        return sorted(keywords)
