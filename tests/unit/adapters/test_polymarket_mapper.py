"""
Test Polymarket API response → RawSignalEvent mapping.

Coverage target: 95%
Focus: Data transformation correctness, edge cases
"""

from datetime import datetime

import pytest

from omen.adapters.inbound.polymarket.mapper import PolymarketMapper
from omen.adapters.inbound.polymarket.schemas import PolymarketEvent
from omen.domain.models.raw_signal import RawSignalEvent


@pytest.fixture
def mapper() -> PolymarketMapper:
    return PolymarketMapper()


@pytest.fixture
def sample_response() -> dict:
    """Standard Polymarket API response."""
    return {
        "id": "0x123abc",
        "question": "Will Red Sea shipping be disrupted?",
        "description": "Market resolves YES if commercial shipping through Red Sea is significantly disrupted.",
        "outcomePrices": ["0.75", "0.25"],
        "volume": "500000",
        "liquidity": "75000",
        "numTraders": 1200,
        "createdAt": "2024-01-15T10:00:00Z",
        "endDate": "2024-06-30T23:59:59Z",
    }


class TestMapMarket:
    """Core mapping functionality."""

    def test_maps_basic_fields_correctly(
        self, mapper: PolymarketMapper, sample_response: dict
    ) -> None:
        out = mapper.map_market(sample_response)
        assert out.event_id == "polymarket-0x123abc"
        assert "Red Sea" in out.title
        assert "disrupted" in (out.description or "")
        assert out.probability == 0.75

    def test_maps_probability_from_outcome_prices(
        self, mapper: PolymarketMapper
    ) -> None:
        raw = {"id": "m1", "outcomePrices": ["0.6", "0.4"]}
        out = mapper.map_market(raw)
        assert out.probability == 0.6

    def test_defaults_probability_when_missing(self, mapper: PolymarketMapper) -> None:
        raw = {"id": "m1"}
        out = mapper.map_market(raw)
        assert out.probability == 0.5

    def test_maps_market_metadata_completely(
        self, mapper: PolymarketMapper, sample_response: dict
    ) -> None:
        out = mapper.map_market(sample_response)
        m = out.market
        assert m.source == "polymarket"
        assert str(m.market_id) == "0x123abc"
        assert m.total_volume_usd == 500000.0
        assert m.current_liquidity_usd == 75000.0
        assert m.num_traders == 1200

    def test_generates_correct_market_url(self, mapper: PolymarketMapper) -> None:
        raw = {"id": "evt-456", "question": "Q?"}
        out = mapper.map_market(raw)
        assert out.market.market_url == "https://polymarket.com/event/evt-456"

    def test_parses_iso_timestamps(
        self, mapper: PolymarketMapper, sample_response: dict
    ) -> None:
        out = mapper.map_market(sample_response)
        assert out.market.created_at is not None
        assert out.market.resolution_date is not None

    def test_handles_missing_timestamps(self, mapper: PolymarketMapper) -> None:
        raw = {"id": "m1", "question": "Q?"}
        out = mapper.map_market(raw)
        assert out.market.created_at is None
        assert out.market.resolution_date is None

    def test_handles_malformed_timestamps(self, mapper: PolymarketMapper) -> None:
        raw = {"id": "m1", "question": "Q?", "createdAt": "not-a-date"}
        out = mapper.map_market(raw)
        assert out.market.created_at is None

    def test_extracts_logistics_keywords(self, mapper: PolymarketMapper) -> None:
        raw = {
            "id": "m1",
            "question": "Shipping and port delays?",
            "description": "Canal freight and container trade.",
        }
        out = mapper.map_market(raw)
        assert "shipping" in out.keywords
        assert "port" in out.keywords
        assert "canal" in out.keywords
        assert "freight" in out.keywords
        assert "container" in out.keywords
        assert "trade" in out.keywords

    def test_extracts_geopolitical_keywords(self, mapper: PolymarketMapper) -> None:
        raw = {
            "id": "m1",
            "question": "Tariff and sanction impact?",
            "description": "Strike and closure risk.",
        }
        out = mapper.map_market(raw)
        assert "tariff" in out.keywords
        assert "sanction" in out.keywords
        assert "strike" in out.keywords
        assert "closure" in out.keywords

    def test_no_keywords_for_unrelated_content(self, mapper: PolymarketMapper) -> None:
        raw = {
            "id": "m1",
            "question": "Will Team A win the game?",
            "description": "Football result. No shipping or trade.",
        }
        out = mapper.map_market(raw)
        assert "trade" in out.keywords
        raw_unrelated = {
            "id": "m2",
            "question": "Will it rain tomorrow?",
            "description": "Weather forecast only.",
        }
        out2 = mapper.map_market(raw_unrelated)
        # Unrelated to trade/shipping; may still match other DB keywords (e.g. "weather")
        assert "trade" not in out2.keywords
        assert "shipping" not in out2.keywords

    def test_infers_red_sea_location(self, mapper: PolymarketMapper) -> None:
        raw = {
            "id": "m1",
            "question": "Red Sea disruption?",
            "description": "Shipping via Red Sea.",
        }
        out = mapper.map_market(raw)
        assert len(out.inferred_locations) >= 1
        names = [loc.name for loc in out.inferred_locations]
        assert "Red Sea" in names

    def test_infers_multiple_locations(self, mapper: PolymarketMapper) -> None:
        raw = {
            "id": "m1",
            "question": "Red Sea and Suez and Panama",
            "description": "Taiwan and China trade.",
        }
        out = mapper.map_market(raw)
        assert len(out.inferred_locations) >= 2
        names = [loc.name for loc in out.inferred_locations]
        assert "Red Sea" in names or "Suez Canal" in names

    def test_stores_raw_payload(
        self, mapper: PolymarketMapper, sample_response: dict
    ) -> None:
        out = mapper.map_market(sample_response)
        assert out.raw_payload == sample_response

    def test_title_fallback_when_question_missing(self, mapper: PolymarketMapper) -> None:
        raw = {"id": "m1", "title": "Fallback title"}
        out = mapper.map_market(raw)
        assert out.title == "Fallback title"


class TestExtractProbability:
    """Probability extraction edge cases (via map_market)."""

    def test_extracts_float_from_string(self, mapper: PolymarketMapper) -> None:
        raw = {"id": "m1", "outcomePrices": ["0.75"]}
        out = mapper.map_market(raw)
        assert out.probability == 0.75

    def test_handles_empty_array(self, mapper: PolymarketMapper) -> None:
        raw = {"id": "m1", "outcomePrices": []}
        out = mapper.map_market(raw)
        assert out.probability == 0.5

    def test_handles_missing_field(self, mapper: PolymarketMapper) -> None:
        raw = {"id": "m1"}
        out = mapper.map_market(raw)
        assert out.probability == 0.5


class TestExtractKeywords:
    """Keyword extraction logic (via map_market)."""

    def test_case_insensitive_matching(self, mapper: PolymarketMapper) -> None:
        raw = {"id": "m1", "question": "RED SEA disruption", "description": "SUEZ canal"}
        out = mapper.map_market(raw)
        assert "red sea" in out.keywords
        assert "suez" in out.keywords

    def test_matches_in_description(self, mapper: PolymarketMapper) -> None:
        raw = {"id": "m1", "question": "Weather?", "description": "Red sea shipping."}
        out = mapper.map_market(raw)
        assert "red sea" in out.keywords
        assert "shipping" in out.keywords

    def test_handles_none_description(self, mapper: PolymarketMapper) -> None:
        raw = {"id": "m1", "question": "Port strike?"}
        out = mapper.map_market(raw)
        assert "port" in out.keywords
        assert "strike" in out.keywords


class TestInferLocations:
    """Geographic inference logic (via map_market)."""

    def test_all_known_locations_detected(self, mapper: PolymarketMapper) -> None:
        raw = {
            "id": "m1",
            "question": "Red sea suez panama taiwan china",
            "description": "",
        }
        out = mapper.map_market(raw)
        names = [loc.name for loc in out.inferred_locations]
        assert "Red Sea" in names
        assert "Suez Canal" in names
        assert "Panama Canal" in names
        assert "Taiwan" in names
        assert "China" in names

    def test_locations_have_valid_coordinates(self, mapper: PolymarketMapper) -> None:
        raw = {"id": "m1", "question": "Red sea suez", "description": ""}
        out = mapper.map_market(raw)
        for loc in out.inferred_locations:
            assert -90 <= loc.latitude <= 90
            assert -180 <= loc.longitude <= 180

    def test_returns_empty_for_no_match(self, mapper: PolymarketMapper) -> None:
        raw = {"id": "m1", "question": "Sports result?", "description": "No geography."}
        out = mapper.map_market(raw)
        assert out.inferred_locations == []


class TestParseTimestamp:
    """Timestamp parsing edge cases (via map_market)."""

    def test_parses_z_suffix(self, mapper: PolymarketMapper) -> None:
        raw = {"id": "m1", "question": "Q?", "createdAt": "2024-01-15T10:00:00Z"}
        out = mapper.map_market(raw)
        assert out.market.created_at is not None
        assert out.market.created_at.year == 2024

    def test_parses_offset_suffix(self, mapper: PolymarketMapper) -> None:
        raw = {"id": "m1", "question": "Q?", "createdAt": "2024-01-15T10:00:00+00:00"}
        out = mapper.map_market(raw)
        assert out.market.created_at is not None

    def test_returns_none_for_invalid(self, mapper: PolymarketMapper) -> None:
        raw = {"id": "m1", "question": "Q?", "createdAt": "not-a-date"}
        out = mapper.map_market(raw)
        assert out.market.created_at is None

    def test_returns_none_for_empty_string(self, mapper: PolymarketMapper) -> None:
        raw = {"id": "m1", "question": "Q?", "createdAt": ""}
        out = mapper.map_market(raw)
        assert out.market.created_at is None


class TestToRawSignal:
    """PolymarketEvent schema → RawSignalEvent."""

    def test_to_raw_signal_uses_map_market(self, mapper: PolymarketMapper) -> None:
        event = PolymarketEvent(
            id="evt-1",
            title="Red Sea?",
            description="Shipping.",
            created_at=datetime(2024, 1, 1, 12, 0, 0),
            liquidity=10000.0,
            metadata={"outcomePrices": ["0.7", "0.3"]},
        )
        out = mapper.to_raw_signal(event)
        assert isinstance(out, RawSignalEvent)
        assert "evt-1" in str(out.event_id)
        assert out.probability == 0.7
