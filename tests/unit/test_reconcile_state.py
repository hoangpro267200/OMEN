"""Unit tests for RiskCast ReconcileStateStore (highwater detection)."""

from pathlib import Path

import pytest

from riskcast.infrastructure.reconcile_state import (
    ReconcileStateStore,
    ReconcileState,
)


@pytest.mark.asyncio
async def test_needs_reconcile_never_reconciled(tmp_path: Path):
    """needs_reconcile returns True when no state exists."""
    store = ReconcileStateStore(tmp_path / "reconcile.db")
    needs, reason = await store.needs_reconcile("2026-01-29", 10, 1)
    assert needs is True
    assert reason == "never_reconciled"


@pytest.mark.asyncio
async def test_needs_reconcile_up_to_date(tmp_path: Path):
    """needs_reconcile returns False when highwater and revision match."""
    store = ReconcileStateStore(tmp_path / "reconcile.db")
    await store.save_state(
        partition_date="2026-01-29",
        ledger_highwater=100,
        manifest_revision=1,
        ledger_record_count=100,
        processed_count=100,
        missing_count=0,
        replayed_count=0,
        status="COMPLETED",
    )
    needs, reason = await store.needs_reconcile("2026-01-29", 100, 1)
    assert needs is False
    assert reason == "up_to_date"


@pytest.mark.asyncio
async def test_needs_reconcile_highwater_increased(tmp_path: Path):
    """needs_reconcile returns True when highwater increased (late arrivals)."""
    store = ReconcileStateStore(tmp_path / "reconcile.db")
    await store.save_state(
        partition_date="2026-01-29",
        ledger_highwater=100,
        manifest_revision=1,
        ledger_record_count=100,
        processed_count=100,
        missing_count=0,
        replayed_count=0,
        status="COMPLETED",
    )
    needs, reason = await store.needs_reconcile("2026-01-29", 105, 1)
    assert needs is True
    assert "highwater_increased" in reason
    assert "100" in reason and "105" in reason


@pytest.mark.asyncio
async def test_needs_reconcile_manifest_revision_ignored(tmp_path: Path):
    """needs_reconcile does NOT trigger on manifest_revision increase (Option A: highwater only)."""
    store = ReconcileStateStore(tmp_path / "reconcile.db")
    await store.save_state(
        partition_date="2026-01-29",
        ledger_highwater=100,
        manifest_revision=1,
        ledger_record_count=100,
        processed_count=100,
        missing_count=0,
        replayed_count=0,
        status="COMPLETED",
    )
    needs, reason = await store.needs_reconcile("2026-01-29", 100, 2)
    assert needs is False
    assert reason == "up_to_date"


@pytest.mark.asyncio
async def test_needs_reconcile_previous_failed(tmp_path: Path):
    """needs_reconcile returns True when previous status was not COMPLETED."""
    store = ReconcileStateStore(tmp_path / "reconcile.db")
    await store.save_state(
        partition_date="2026-01-29",
        ledger_highwater=100,
        manifest_revision=1,
        ledger_record_count=100,
        processed_count=90,
        missing_count=10,
        replayed_count=0,
        status="PARTIAL",
    )
    needs, reason = await store.needs_reconcile("2026-01-29", 100, 1)
    assert needs is True
    assert "previous_status" in reason


@pytest.mark.asyncio
async def test_get_state_after_save(tmp_path: Path):
    """get_state returns ReconcileState after save_state."""
    store = ReconcileStateStore(tmp_path / "reconcile.db")
    await store.save_state(
        partition_date="2026-01-30",
        ledger_highwater=50,
        manifest_revision=1,
        ledger_record_count=50,
        processed_count=50,
        missing_count=0,
        replayed_count=0,
        status="COMPLETED",
    )
    state = await store.get_state("2026-01-30")
    assert state is not None
    assert isinstance(state, ReconcileState)
    assert state.partition_date == "2026-01-30"
    assert state.ledger_highwater == 50
    assert state.status == "COMPLETED"
