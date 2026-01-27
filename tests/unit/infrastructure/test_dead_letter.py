"""Tests for dead letter queue."""

import pytest

from omen.domain.errors import OmenError, ValidationRuleError
from omen.domain.models.common import EventId, MarketId
from omen.domain.models.raw_signal import RawSignalEvent, MarketMetadata
from omen.infrastructure.dead_letter import DeadLetterQueue, DeadLetterEntry


@pytest.fixture
def sample_event() -> RawSignalEvent:
    return RawSignalEvent(
        event_id=EventId("dlq-test-1"),
        title="Test",
        probability=0.5,
        market=MarketMetadata(
            source="t",
            market_id=MarketId("m1"),
            total_volume_usd=1000.0,
            current_liquidity_usd=500.0,
        ),
    )


class TestDeadLetterQueue:
    """DLQ stores failed events and allows peek/pop/by_id."""

    def test_add_and_pop(self, sample_event):
        dlq = DeadLetterQueue(max_size=10)
        err = OmenError("failed", context={"step": "validation"})
        entry = dlq.add(sample_event, err)
        assert entry.event.event_id == sample_event.event_id
        assert entry.error.message == "failed"
        assert entry.retry_count == 0
        assert dlq.size() == 1
        popped = dlq.pop()
        assert popped is not None
        assert popped.event.event_id == sample_event.event_id
        assert dlq.size() == 0
        assert dlq.pop() is None

    def test_peek_does_not_remove(self, sample_event):
        dlq = DeadLetterQueue(max_size=10)
        dlq.add(sample_event, OmenError("x"))
        a = dlq.peek(5)
        assert len(a) == 1
        assert dlq.size() == 1
        dlq.peek(5)
        assert dlq.size() == 1

    def test_get_by_event_id(self, sample_event):
        dlq = DeadLetterQueue(max_size=10)
        dlq.add(sample_event, OmenError("x"))
        found = dlq.get_by_event_id(str(sample_event.event_id))
        assert found is not None
        assert found.event.event_id == sample_event.event_id
        assert dlq.get_by_event_id("nonexistent") is None

    def test_clear_returns_count(self, sample_event):
        dlq = DeadLetterQueue(max_size=10)
        dlq.add(sample_event, OmenError("a"))
        dlq.add(
            RawSignalEvent(
                event_id=EventId("e2"),
                title="T",
                probability=0.5,
                market=MarketMetadata(
                    source="t", market_id=MarketId("m2"),
                    total_volume_usd=1.0, current_liquidity_usd=1.0,
                ),
            ),
            OmenError("b"),
        )
        n = dlq.clear()
        assert n == 2
        assert dlq.is_empty()
        assert dlq.size() == 0

    def test_entry_to_dict(self, sample_event):
        err = ValidationRuleError("rule broke", rule_name="liquidity")
        entry = DeadLetterEntry(
            event=sample_event,
            error=err,
            failed_at=err.timestamp,
            retry_count=1,
        )
        d = entry.to_dict()
        assert d["event_id"] == str(sample_event.event_id)
        assert d["event_hash"] == sample_event.input_event_hash
        assert d["retry_count"] == 1
        assert d["error"]["error_type"] == "ValidationRuleError"

    def test_max_size_evicts_oldest(self, sample_event):
        dlq = DeadLetterQueue(max_size=2)
        e2 = RawSignalEvent(
            event_id=EventId("e2"),
            title="T",
            probability=0.5,
            market=MarketMetadata(
                source="t", market_id=MarketId("m2"),
                total_volume_usd=1.0, current_liquidity_usd=1.0,
            ),
        )
        e3 = RawSignalEvent(
            event_id=EventId("e3"),
            title="T",
            probability=0.5,
            market=MarketMetadata(
                source="t", market_id=MarketId("m3"),
                total_volume_usd=1.0, current_liquidity_usd=1.0,
            ),
        )
        dlq.add(sample_event, OmenError("1"))
        dlq.add(e2, OmenError("2"))
        dlq.add(e3, OmenError("3"))
        assert dlq.size() == 2
        first = dlq.pop()
        assert first is not None and str(first.event.event_id) == "e2"
        second = dlq.pop()
        assert second is not None and str(second.event.event_id) == "e3"
