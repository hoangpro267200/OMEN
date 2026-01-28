"""Tests for real-time price streamer (register/subscribe mapping)."""

import pytest
from unittest.mock import AsyncMock, patch

from omen.infrastructure.realtime.price_streamer import (
    PriceStreamer,
    get_price_streamer,
    SignalPriceUpdate,
)


class TestPriceStreamer:
    """PriceStreamer registration and lookup."""

    def test_register_signal_creates_mapping(self):
        """Registering a signal should create token mapping."""
        streamer = PriceStreamer()
        streamer.register_signal(
            signal_id="OMEN-TEST-001",
            token_id="0x1234567890abcdef",
            initial_price=0.75,
        )
        assert streamer.get_registered_count() == 1
        assert streamer.is_registered("OMEN-TEST-001")
        assert streamer.get_token_for_signal("OMEN-TEST-001") == "0x1234567890abcdef"
        assert streamer.get_registered_signals() == ["OMEN-TEST-001"]

    def test_unregistered_signal_not_found(self):
        """Unregistered signal should not be found."""
        streamer = PriceStreamer()
        assert not streamer.is_registered("OMEN-FAKE-001")
        assert streamer.get_token_for_signal("OMEN-FAKE-001") is None

    @pytest.mark.asyncio
    async def test_subscribe_only_registered_signals(self):
        """Subscribe should return only registered signal IDs and call client with their tokens."""
        streamer = PriceStreamer()
        streamer.register_signal("OMEN-001", "token-001", 0.5)

        with patch.object(
            streamer._ws_client,
            "subscribe",
            new_callable=AsyncMock,
        ) as mock_sub:
            subscribed = await streamer.subscribe_signals(["OMEN-001", "OMEN-002"])
            assert subscribed == ["OMEN-001"]
            mock_sub.assert_called_once_with(["token-001"])

    def test_signal_price_update_fields(self):
        """SignalPriceUpdate has required fields for SSE."""
        update = SignalPriceUpdate(
            signal_id="OMEN-X",
            new_probability=0.8,
            old_probability=0.7,
            change_percent=14.28,
            timestamp="2024-01-28T12:00:00Z",
        )
        assert update.signal_id == "OMEN-X"
        assert update.new_probability == 0.8
        assert update.change_percent == 14.28


class TestGetPriceStreamer:
    """Singleton accessor."""

    def test_returns_same_instance(self):
        """get_price_streamer returns the same instance on repeated calls."""
        a = get_price_streamer()
        b = get_price_streamer()
        assert a is b
