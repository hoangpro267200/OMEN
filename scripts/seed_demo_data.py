"""
Seed demo data: 10 signals to ledger, 8 to RiskCast (2 missing for reconcile demo).

Usage:
    python -m scripts.seed_demo_data

Expects: OMEN_LEDGER_BASE_PATH, RISKCAST_INGEST_URL (or OMEN_RISKCAST_URL), RISKCAST_API_KEYS.
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add repo root and src for imports
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

# ruff: noqa: E402
from omen.domain.models.omen_signal import (
    ConfidenceLevel,
    OmenSignal,
    SignalCategory,
)
from omen.domain.models.signal_event import (
    SignalEvent,
    generate_input_event_hash,
)
from omen.infrastructure.ledger.writer import LedgerWriter

logger = logging.getLogger(__name__)

# Category mapping: demo_signals category string -> SignalCategory
_CATEGORY_MAP = {
    "GEOPOLITICAL": SignalCategory.GEOPOLITICAL,
    "INFRASTRUCTURE": SignalCategory.INFRASTRUCTURE,
    "CLIMATE": SignalCategory.WEATHER,
    "COMPLIANCE": SignalCategory.REGULATORY,
    "OPERATIONAL": SignalCategory.OTHER,
    "FINANCIAL": SignalCategory.ECONOMIC,
    "NETWORK": SignalCategory.OTHER,
}


def _build_omen_signal(raw: dict) -> OmenSignal:
    """Build OmenSignal from demo_signals dict."""
    cat_str = raw.get("category", "OTHER")
    category = _CATEGORY_MAP.get(cat_str, SignalCategory.OTHER)
    conf_str = raw.get("confidence_level", "MEDIUM")
    confidence_level = (
        ConfidenceLevel.HIGH
        if conf_str == "HIGH"
        else ConfidenceLevel.LOW
        if conf_str == "LOW"
        else ConfidenceLevel.MEDIUM
    )
    return OmenSignal(
        signal_id=raw["id"],
        source_event_id=f"demo-{raw['id']}",
        title=raw["title"],
        description=raw.get("description"),
        probability=float(raw["probability"]),
        confidence_score=float(raw["confidence_score"]),
        confidence_level=confidence_level,
        category=category,
        ruleset_version="1.0.0",
        trace_id=f"trace-{raw['id'][:12]}",
    )


def _build_signal_event(omen_signal: OmenSignal, observed_at: datetime) -> SignalEvent:
    """Build SignalEvent from OmenSignal."""
    input_hash = generate_input_event_hash(
        {"id": omen_signal.signal_id, "title": omen_signal.title}
    )
    return SignalEvent.from_omen_signal(
        signal=omen_signal,
        input_event_hash=input_hash,
        observed_at=observed_at,
    )


async def create_demo_signals(
    total_signals: int = 10,
    processed_count: int = 8,
) -> None:
    """
    Seed ledger with total_signals and ingest processed_count to RiskCast.
    The first (total_signals - processed_count) of the "missing" set are not ingested.
    """
    from data.demo_signals import DEMO_SIGNALS, MISSING_SIGNAL_IDS

    ledger_path = os.environ.get("OMEN_LEDGER_BASE_PATH", "/data/ledger")
    riskcast_url = os.environ.get("RISKCAST_INGEST_URL") or os.environ.get(
        "OMEN_RISKCAST_URL", "http://localhost:8001"
    )
    ingest_url = riskcast_url.rstrip("/") + "/api/v1/signals/ingest"
    api_keys = os.environ.get("RISKCAST_API_KEYS", "dev-key-123")
    api_key = api_keys.strip().split(",")[0].strip()

    writer = LedgerWriter(Path(ledger_path))
    observed_at = datetime.now(timezone.utc)

    # Take exactly total_signals from DEMO_SIGNALS
    signals_to_seed = DEMO_SIGNALS[:total_signals]
    ids_to_skip_ingest = set(MISSING_SIGNAL_IDS)  # 2 missing for reconcile demo

    written_events: list[SignalEvent] = []

    for raw in signals_to_seed:
        omen_signal = _build_omen_signal(raw)
        event = _build_signal_event(omen_signal, observed_at)
        written = writer.write(event)
        written_events.append(written)

    # Ingest to RiskCast (only those not in ids_to_skip_ingest = 8 processed)
    import httpx

    async with httpx.AsyncClient(timeout=10.0) as client:
        for event in written_events:
            if event.signal_id not in ids_to_skip_ingest:
                body = event.model_dump(mode="json")
                try:
                    r = await client.post(
                        ingest_url,
                        json=body,
                        headers={
                            "Content-Type": "application/json",
                            "Authorization": f"Bearer {api_key}",
                            "X-Idempotency-Key": event.signal_id,
                        },
                    )
                    if r.status_code not in (200, 201, 409):
                        logger.warning(
                            "Ingest %s: %s %s",
                            event.signal_id,
                            r.status_code,
                            r.text[:200],
                        )
                except Exception as e:
                    logger.warning("Ingest %s failed: %s", event.signal_id, e)

    ingested_count = sum(1 for e in written_events if e.signal_id not in ids_to_skip_ingest)
    logger.info(
        "Seeded ledger with %s signals, ingested %s to RiskCast (%s missing for reconcile)",
        len(written_events),
        ingested_count,
        len(ids_to_skip_ingest),
    )


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    asyncio.run(create_demo_signals(total_signals=10, processed_count=8))
