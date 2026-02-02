"""
MANDATORY: RiskCast concurrent ingest dedupe test.
Send same signal_id concurrently (>=20 requests);
exactly 1 returns 200 accepted, rest return 409 duplicate with original ack_id;
DB must contain exactly 1 row for that signal_id.
"""

import asyncio
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import httpx
import pytest
from httpx import ASGITransport

from omen.domain.models.omen_signal import (
    OmenSignal,
    ConfidenceLevel,
    SignalCategory,
    GeographicContext,
    TemporalContext,
)
from omen.domain.models.impact_hints import ImpactHints
from omen.domain.models.signal_event import SignalEvent
from omen.domain.models.enums import SignalType, SignalStatus
from riskcast.api.app import app
from riskcast.infrastructure.signal_store import SignalStore


def _make_minimal_signal(signal_id: str = "OMEN-DEDUPE001") -> OmenSignal:
    return OmenSignal(
        signal_id=signal_id,
        source_event_id="dedupe-test",
        trace_id="trace-dedupe",
        title="Dedupe Test",
        probability=0.5,
        probability_source="test",
        confidence_score=0.7,
        confidence_level=ConfidenceLevel.MEDIUM,
        confidence_factors={},
        category=SignalCategory.OTHER,
        geographic=GeographicContext(),
        temporal=TemporalContext(),
        impact_hints=ImpactHints(),
        evidence=[],
        ruleset_version="1.0.0",
        generated_at=datetime.now(timezone.utc),
        signal_type=SignalType.UNCLASSIFIED,
        status=SignalStatus.ACTIVE,
    )


def _make_event_payload(signal_id: str = "OMEN-DEDUPE001") -> dict:
    signal = _make_minimal_signal(signal_id=signal_id)
    event = SignalEvent.from_omen_signal(
        signal=signal,
        input_event_hash="sha256:dedupe",
        observed_at=datetime.now(timezone.utc),
    )
    return event.model_dump(mode="json")


@pytest.mark.asyncio
async def test_concurrent_ingest_dedupe(tmp_path: Path):
    """
    MANDATORY: Send same signal_id concurrently (>=20 requests).
    Exactly 1 returns 200 with ack_id; rest return 409 with original ack_id.
    DB contains exactly 1 row for that signal_id.
    """
    db_path = tmp_path / "signals.db"
    store = SignalStore(db_path)

    async def post_once(client: httpx.AsyncClient, payload: dict):
        return await client.post(
            "/api/v1/signals/ingest",
            json=payload,
            headers={"X-Idempotency-Key": payload["signal_id"]},
        )

    payload = _make_event_payload("OMEN-CONCURRENT-DEDUPE")

    with patch("riskcast.api.routes.ingest.get_store", return_value=store):
        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client:
            # Deterministic: first request wins 200, then 19 concurrent get 409 with original ack_id
            first = await post_once(client, payload)
            assert first.status_code == 200, f"First ingest must succeed: {first.text}"
            first_ack = first.json().get("ack_id")
            assert first_ack and first_ack.startswith("riskcast-ack-")

            tasks = [post_once(client, payload) for _ in range(19)]
            results = await asyncio.gather(*tasks, return_exceptions=True)

    dup = [r for r in results if not isinstance(r, Exception) and r.status_code == 409]
    err = [
        r
        for r in results
        if isinstance(r, Exception) or (getattr(r, "status_code", None) not in (200, 409))
    ]

    assert len(dup) == 19, f"Expected 19x 409, got {len(dup)}; err={err}"
    assert len(err) == 0, f"Unexpected responses: {err}"
    assert first_ack and first_ack.startswith("riskcast-ack-")
    for r in dup:
        assert r.json().get("ack_id") == first_ack
        assert r.json().get("duplicate") is True

    rec = await store.get_by_signal_id("OMEN-CONCURRENT-DEDUPE")
    assert rec is not None
    assert rec.ack_id == first_ack
    ids = await store.list_processed_ids(rec.emitted_at.date().isoformat())
    count = sum(1 for i in ids if i == "OMEN-CONCURRENT-DEDUPE")
    assert count == 1, f"DB must contain exactly 1 row for signal_id, got {count}"
