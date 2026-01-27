"""Inbound adapters for data ingestion."""

from omen.adapters.inbound.stub_source import StubSignalSource

try:
    from omen.adapters.inbound.polymarket.client import PolymarketClient
    from omen.adapters.inbound.polymarket.mapper import PolymarketMapper
except ImportError:
    PolymarketClient = None  # type: ignore[misc, assignment]
    PolymarketMapper = None  # type: ignore[misc, assignment]

__all__ = ["StubSignalSource", "PolymarketClient", "PolymarketMapper"]
