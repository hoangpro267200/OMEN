"""Unit tests for RiskCast async SignalStore (aiosqlite)."""

from datetime import datetime
from pathlib import Path

import pytest

from riskcast.infrastructure.signal_store import (
    SignalStore,
    ProcessedSignal,
)


@pytest.mark.asyncio
async def test_store_and_get_by_signal_id(tmp_path: Path):
    """Store then get_by_signal_id returns ProcessedSignal."""
    db_path = tmp_path / "signals.db"
    store = SignalStore(db_path)

    ack_id = await store.store(
        signal_id="OMEN-STORE01",
        trace_id="trace-a",
        source_event_id="ev-1",
        ack_id=None,
        processed_at=datetime.utcnow(),
        emitted_at=datetime.utcnow(),
        source="hot_path",
        signal_data={"title": "Test"},
    )
    assert ack_id.startswith("riskcast-ack-")
    assert len(ack_id) == len("riskcast-ack-") + 16

    rec = await store.get_by_signal_id("OMEN-STORE01")
    assert rec is not None
    assert isinstance(rec, ProcessedSignal)
    assert rec.signal_id == "OMEN-STORE01"
    assert rec.ack_id == ack_id
    assert rec.signal_data == {"title": "Test"}


@pytest.mark.asyncio
async def test_get_by_signal_id_missing_returns_none(tmp_path: Path):
    """get_by_signal_id returns None when not found."""
    store = SignalStore(tmp_path / "signals.db")
    rec = await store.get_by_signal_id("nonexistent")
    assert rec is None


@pytest.mark.asyncio
async def test_list_processed_ids(tmp_path: Path):
    """list_processed_ids returns signal_ids for partition."""
    store = SignalStore(tmp_path / "signals.db")
    now = datetime.utcnow()
    partition = now.date().isoformat()

    await store.store(
        signal_id="OMEN-L1",
        trace_id="t1",
        source_event_id="e1",
        ack_id=None,
        processed_at=now,
        emitted_at=now,
        source="hot_path",
        signal_data={},
    )
    ids = await store.list_processed_ids(partition)
    assert "OMEN-L1" in ids


@pytest.mark.asyncio
async def test_count_by_source(tmp_path: Path):
    """count_by_source returns counts per source."""
    store = SignalStore(tmp_path / "signals.db")
    now = datetime.utcnow()
    partition = now.date().isoformat()

    await store.store(
        signal_id="OMEN-C1",
        trace_id="t1",
        source_event_id="e1",
        ack_id=None,
        processed_at=now,
        emitted_at=now,
        source="hot_path",
        signal_data={},
    )
    await store.store(
        signal_id="OMEN-C2",
        trace_id="t2",
        source_event_id="e2",
        ack_id=None,
        processed_at=now,
        emitted_at=now,
        source="reconcile",
        signal_data={},
    )
    counts = await store.count_by_source(partition)
    assert counts.get("hot_path") == 1
    assert counts.get("reconcile") == 1


@pytest.mark.asyncio
async def test_ack_id_uuid_no_collision(tmp_path: Path):
    """Generated ack_ids are unique (UUID-based)."""
    store = SignalStore(tmp_path / "signals.db")
    now = datetime.utcnow()
    acks = set()
    for i in range(5):
        ack = await store.store(
            signal_id=f"OMEN-U{i}",
            trace_id=f"t{i}",
            source_event_id=f"e{i}",
            ack_id=None,
            processed_at=now,
            emitted_at=now,
            source="hot_path",
            signal_data={},
        )
        acks.add(ack)
    assert len(acks) == 5
