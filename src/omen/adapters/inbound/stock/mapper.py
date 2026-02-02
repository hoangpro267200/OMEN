"""
Stock mapper.

Maps stock quotes and spikes to RawSignalEvent for pipeline processing.
"""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone

from omen.adapters.inbound.stock.config import StockConfig, StockWatchlistItem
from omen.adapters.inbound.stock.schemas import StockQuote, StockSpike
from omen.domain.models.common import GeoLocation, ProbabilityMovement
from omen.domain.models.raw_signal import MarketMetadata, RawSignalEvent

logger = logging.getLogger(__name__)


def _map_region_to_locations(region: str) -> list[GeoLocation]:
    """Map stock region to geographic locations."""
    region_map = {
        "us": [
            GeoLocation(
                name="United States", region="North America", latitude=37.0902, longitude=-95.7129
            )
        ],
        "vietnam": [
            GeoLocation(
                name="Vietnam", region="Southeast Asia", latitude=14.0583, longitude=108.2772
            )
        ],
        "global": [GeoLocation(name="Global", region="Global", latitude=0.0, longitude=0.0)],
        "europe": [
            GeoLocation(name="Europe", region="Europe", latitude=54.5260, longitude=15.2551)
        ],
        "asia": [GeoLocation(name="Asia", region="Asia", latitude=34.0479, longitude=100.6197)],
    }
    return region_map.get(
        region, [GeoLocation(name="Global", region="Global", latitude=0.0, longitude=0.0)]
    )


def _estimate_probability_from_change(change_pct: float, spike: StockSpike | None) -> float:
    """
    Estimate probability based on price movement.

    This represents probability of trend continuation.
    Bounded between 0.3 and 0.85 to avoid extreme values.
    """
    # Base probability: 50%
    base_prob = 0.5

    # Adjust based on magnitude of change
    # Every 1% change adds 0.02 to probability (up to 0.2)
    magnitude_adj = min(abs(change_pct) * 0.02, 0.2)

    if spike:
        # Additional boost for detected spikes
        severity_adj = {
            "minor": 0.02,
            "moderate": 0.05,
            "major": 0.08,
            "extreme": 0.10,
        }
        magnitude_adj += severity_adj.get(spike.severity, 0.0)

    prob = base_prob + magnitude_adj

    # Bound to [0.3, 0.85]
    return max(0.3, min(0.85, prob))


class StockMapper:
    """Maps stock data to RawSignalEvent."""

    def __init__(self, config: StockConfig):
        self.config = config

    def map_quote(
        self,
        quote: StockQuote,
        item: StockWatchlistItem,
        spike: StockSpike | None = None,
    ) -> RawSignalEvent | None:
        """Map a stock quote to RawSignalEvent."""

        # Determine if this is significant enough to emit
        if spike is None and abs(quote.change_pct) < item.spike_threshold_pct:
            return None

        now = datetime.now(timezone.utc)

        # Build deterministic event_id
        date_str = quote.timestamp.strftime("%Y%m%d%H")
        event_id = f"stock-{quote.symbol.lower()}-{date_str}"

        # Build title based on movement
        direction = "tăng" if quote.change_pct > 0 else "giảm"
        direction_en = "up" if quote.change_pct > 0 else "down"

        title = f"{quote.name} ({quote.symbol}) {direction} {abs(quote.change_pct):.2f}%"

        description = (
            f"{quote.name} moved {direction_en} {abs(quote.change_pct):.2f}% "
            f"from {quote.previous_close:,.2f} to {quote.price:,.2f} {quote.currency}. "
        )

        if spike:
            description += f"Severity: {spike.severity}. {spike.impact_hint}"

        # Calculate probability
        probability = _estimate_probability_from_change(quote.change_pct, spike)
        prev_probability = 0.5

        # Build movement
        movement = ProbabilityMovement(
            current=probability,
            previous=prev_probability,
            delta=probability - prev_probability,
            window_hours=24,
        )

        # Build MarketMetadata (required fields: source, market_id, total_volume_usd, current_liquidity_usd)
        market = MarketMetadata(
            source="stock",
            market_id=f"stock-{quote.symbol.lower()}",
            total_volume_usd=float(quote.volume) * quote.price if quote.price > 0 else 0.0,
            current_liquidity_usd=(
                float(quote.volume) * quote.price / 1000 if quote.price > 0 else 0.0
            ),
            created_at=now,
        )

        # Build keywords
        keywords = self._generate_keywords(quote, spike)

        # Source metrics for additional context
        source_metrics = {
            "provider": quote.provider,
            "category": quote.category,
            "region": quote.region,
            "price": quote.price,
            "previous_close": quote.previous_close,
            "change_pct": quote.change_pct,
            "volume": quote.volume,
            "currency": quote.currency,
        }

        if spike:
            source_metrics.update(
                {
                    "spike_severity": spike.severity,
                    "spike_zscore": spike.zscore,
                    "spike_direction": spike.direction,
                    "impact_hint": spike.impact_hint,
                }
            )

        return RawSignalEvent(
            event_id=event_id,
            title=title,
            description=description,
            probability=probability,
            movement=movement,
            keywords=keywords,
            inferred_locations=_map_region_to_locations(quote.region),
            market=market,
            observed_at=quote.timestamp,
            source_metrics=source_metrics,
        )

    def _generate_keywords(self, quote: StockQuote, spike: StockSpike | None) -> list[str]:
        """Generate keywords for the event."""
        keywords = [quote.category, quote.region, quote.provider, quote.symbol.lower()]

        if quote.change_pct > 0:
            keywords.append("bullish")
        else:
            keywords.append("bearish")

        if spike:
            keywords.append(f"spike_{spike.severity}")
            if spike.severity in ("major", "extreme"):
                keywords.append("high_impact")

        # Category-specific keywords
        category_keywords = {
            "volatility": ["risk_indicator", "vix", "fear_gauge"],
            "bond": ["interest_rate", "treasury", "yield"],
            "forex": ["currency", "exchange_rate", "fx"],
            "commodity": ["raw_material", "energy", "metals"],
            "index": ["market_index", "equity", "benchmark"],
            "stock": ["equity", "company", "earnings"],
        }

        keywords.extend(category_keywords.get(quote.category, []))

        return list(set(keywords))


def map_quote_to_event(
    quote: StockQuote,
    item: StockWatchlistItem,
    spike: StockSpike | None = None,
    config: StockConfig | None = None,
) -> RawSignalEvent | None:
    """Convenience function to map quote to event."""
    if config is None:
        config = StockConfig()
    mapper = StockMapper(config)
    return mapper.map_quote(quote, item, spike)
