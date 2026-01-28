"""Map Polymarket API responses to OMEN domain models."""

import json
from datetime import datetime
from typing import Any

from omen.adapters.inbound.polymarket.schemas import PolymarketEvent
from omen.domain.models.common import EventId, GeoLocation, MarketId
from omen.domain.models.raw_signal import MarketMetadata, RawSignalEvent


def _safe_float(value: Any, default: float = 0.0) -> float:
    """Safely convert to float."""
    if value is None:
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


class PolymarketMapper:
    """
    Maps Polymarket API responses to RawSignalEvent.

    Normalizes Polymarket's format into OMEN's market-agnostic internal format.
    """

    def map_market(self, raw: dict[str, Any]) -> RawSignalEvent:
        """
        Map a single Polymarket market (raw API response) to RawSignalEvent.

        Args:
            raw: Raw API response for a market.

        Returns:
            Normalized RawSignalEvent.
        """
        event_id = EventId(f"polymarket-{raw.get('id', '')}")
        title = str(raw.get("question") or raw.get("title") or "")[:500] or "Untitled"
        description = raw.get("description")
        if description is not None:
            description = str(description)[:5000]

        probability = self._extract_probability(raw)
        condition_id = raw.get("conditionId") or raw.get("condition_id")
        clob_token_ids = self._parse_clob_token_ids(
            raw.get("clobTokenIds") or raw.get("clob_token_ids")
        )
        market = MarketMetadata(
            source="polymarket",
            market_id=MarketId(str(raw.get("id", ""))),
            market_url=(
                f"https://polymarket.com/event/{raw.get('id', '')}"
                if raw.get("id") else None
            ),
            created_at=self._parse_timestamp(raw.get("createdAt")),
            resolution_date=self._parse_timestamp(raw.get("endDate")),
            total_volume_usd=float(raw.get("volume") or 0),
            current_liquidity_usd=float(raw.get("liquidity") or 0),
            num_traders=int(raw["numTraders"]) if raw.get("numTraders") is not None else None,
            condition_token_id=condition_id,
            clob_token_ids=clob_token_ids,
        )
        keywords = self._extract_keywords(title, description)
        locations = self._infer_locations(title, description)

        return RawSignalEvent(
            event_id=event_id,
            title=title,
            description=description,
            probability=probability,
            movement=None,
            keywords=keywords,
            inferred_locations=locations,
            market=market,
            observed_at=self._parse_timestamp(raw.get("createdAt")) or datetime.utcnow(),
            market_last_updated=None,
            raw_payload=raw,
        )

    def to_raw_signal(self, event: PolymarketEvent) -> RawSignalEvent:
        """Convert PolymarketEvent (schema) to RawSignalEvent. Uses map_market internally."""
        raw = {
            "id": event.id,
            "title": event.title,
            "question": event.title,
            "description": event.description or "",
            "createdAt": event.created_at.isoformat() if event.created_at else None,
            "liquidity": event.liquidity,
            "volume": (float(event.liquidity) * 10) if event.liquidity else 0,
            "numTraders": None,
            **event.metadata,
        }
        return self.map_market(raw)

    def _extract_probability(self, raw: dict[str, Any]) -> float:
        """Extract YES probability from Polymarket response (CLOB or Gamma)."""
        prices = raw.get("outcomePrices") or raw.get("outcome_prices")
        if isinstance(prices, str):
            try:
                parsed = json.loads(prices)
                if isinstance(parsed, (list, tuple)) and len(parsed) >= 1:
                    return max(0.0, min(1.0, float(parsed[0])))
            except (json.JSONDecodeError, TypeError, ValueError):
                pass
            if "," in prices:
                try:
                    yes_price = float(prices.split(",")[0].strip())
                    return max(0.0, min(1.0, yes_price))
                except (ValueError, IndexError):
                    pass
        if isinstance(prices, (list, tuple)) and len(prices) >= 1:
            try:
                return max(0.0, min(1.0, float(prices[0])))
            except (TypeError, ValueError):
                pass
        p = raw.get("probability") or raw.get("bestAsk") or raw.get("price")
        if p is not None:
            try:
                return max(0.0, min(1.0, float(p)))
            except (TypeError, ValueError):
                pass
        return 0.5

    def _extract_keywords(self, title: str, description: str | None) -> list[str]:
        """Extract logistics-relevant keywords from text."""
        logistics_keywords = {
            "shipping", "port", "canal", "freight", "container",
            "trade", "tariff", "sanction", "strike", "closure",
            "red sea", "suez", "panama", "malacca", "taiwan",
        }
        text = f"{title} {description or ''}".lower()
        return [kw for kw in logistics_keywords if kw in text]

    def _infer_locations(self, title: str, description: str | None) -> list[GeoLocation]:
        """Infer geographic locations from text."""
        hints = {
            "red sea": GeoLocation(latitude=20.0, longitude=38.0, name="Red Sea"),
            "suez": GeoLocation(latitude=30.5, longitude=32.3, name="Suez Canal"),
            "panama": GeoLocation(latitude=9.1, longitude=-79.7, name="Panama Canal"),
            "taiwan": GeoLocation(latitude=23.5, longitude=121.0, name="Taiwan"),
            "china": GeoLocation(latitude=35.0, longitude=105.0, name="China"),
        }
        text = f"{title} {description or ''}".lower()
        return [loc for hint, loc in hints.items() if hint in text]

    def _parse_timestamp(self, ts: Any) -> datetime | None:
        """Parse ISO timestamp string."""
        if ts is None:
            return None
        if isinstance(ts, datetime):
            return ts
        try:
            s = str(ts).replace("Z", "+00:00")
            return datetime.fromisoformat(s)
        except (ValueError, TypeError):
            return None

    def _parse_clob_token_ids(self, value: Any) -> list[str] | None:
        """Parse CLOB token IDs from API (may be list or JSON string)."""
        if value is None:
            return None
        if isinstance(value, list):
            return [str(x) for x in value if x]
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
                if isinstance(parsed, list):
                    return [str(x) for x in parsed if x]
            except (json.JSONDecodeError, TypeError):
                pass
        return None

    def map_event(self, event: dict[str, Any]) -> list[RawSignalEvent]:
        """
        Map a Polymarket Gamma API event (with nested markets) to RawSignalEvent(s).
        One event can have multiple markets -> one RawSignalEvent per market.
        """
        signals: list[RawSignalEvent] = []
        markets = event.get("markets") or []
        if not markets:
            mid = event.get("id") or event.get("conditionId")
            if mid:
                markets = [event]
        for market in markets:
            s = self._map_single_market(event, market)
            if s is not None:
                signals.append(s)
        return signals

    def _map_single_market(
        self, event: dict[str, Any], market: dict[str, Any]
    ) -> RawSignalEvent | None:
        """Map one Gamma event + market to RawSignalEvent."""
        market_id = market.get("id") or market.get("conditionId") or event.get("id")
        if not market_id:
            return None
        title = str(
            market.get("question") or event.get("title") or "Untitled"
        )[:500]
        description = market.get("description") or event.get("description")
        if description is not None:
            description = str(description)[:5000]
        probability = self._extract_probability(market)
        volume = _safe_float(
            market.get("volumeNum") or market.get("volume"), 0.0
        )
        liquidity = _safe_float(
            market.get("liquidityNum") or market.get("liquidity"), 0.0
        )
        num_traders = market.get("numTraders")
        if num_traders is not None:
            try:
                num_traders = int(num_traders)
            except (TypeError, ValueError):
                num_traders = None
        condition_id = (
            market.get("conditionId")
            or market.get("condition_id")
            or event.get("conditionId")
            or event.get("condition_id")
        )
        clob_token_ids = self._parse_clob_token_ids(
            market.get("clobTokenIds")
            or market.get("clob_token_ids")
            or event.get("clobTokenIds")
            or event.get("clob_token_ids")
        )
        metadata = MarketMetadata(
            source="polymarket",
            market_id=MarketId(str(market_id)),
            market_url=f"https://polymarket.com/event/{event.get('slug', event.get('id', market_id))}",
            created_at=self._parse_timestamp(event.get("startDate") or event.get("createdAt")),
            resolution_date=self._parse_timestamp(event.get("endDate") or market.get("endDate")),
            total_volume_usd=volume,
            current_liquidity_usd=liquidity,
            num_traders=num_traders,
            condition_token_id=condition_id,
            clob_token_ids=clob_token_ids,
        )
        keywords = self._extract_keywords(title, description)
        locations = self._infer_locations(title, description)
        return RawSignalEvent(
            event_id=EventId(f"polymarket-{market_id}"),
            title=title,
            description=description or None,
            probability=probability,
            movement=None,
            keywords=keywords,
            inferred_locations=locations,
            market=metadata,
            observed_at=datetime.utcnow(),
            market_last_updated=None,
            raw_payload={"event": event, "market": market},
        )
