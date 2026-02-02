"""
CLI runner for OMEN pipeline.

Usage: python -m scripts.run_pipeline [--source stub|polymarket] [--limit N]
"""

import argparse
import sys
from pathlib import Path

# Ensure package is on path when run as script
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from omen.application.pipeline import OmenPipeline, PipelineConfig
from omen.domain.services.signal_validator import SignalValidator
from omen.domain.services.signal_enricher import SignalEnricher
from omen.domain.rules.validation.liquidity_rule import LiquidityValidationRule
from omen.adapters.inbound.stub_source import StubSignalSource
from omen.adapters.persistence.in_memory_repository import InMemorySignalRepository
from omen.adapters.outbound.console_publisher import ConsolePublisher


def main() -> None:
    parser = argparse.ArgumentParser(description="Run OMEN pipeline")
    parser.add_argument(
        "--source",
        choices=["stub", "polymarket"],
        default="stub",
        help="Signal source (default: stub)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Max events to process (default: 10)",
    )
    args = parser.parse_args()

    # Build components (signal-only pipeline; for impact use omen_impact.LegacyPipeline)
    validator = SignalValidator(rules=[LiquidityValidationRule()])
    enricher = SignalEnricher()
    repository = InMemorySignalRepository()
    publisher = ConsolePublisher()

    pipeline = OmenPipeline(
        validator=validator,
        enricher=enricher,
        repository=repository,
        publisher=publisher,
        config=PipelineConfig.default(),
    )

    # Fetch and process
    if args.source == "stub":
        source = StubSignalSource()
    else:
        # Use Polymarket source
        from omen.adapters.inbound.polymarket.source import PolymarketSignalSource
        from omen.adapters.inbound.polymarket.live_client import PolymarketLiveClient
        from omen.adapters.inbound.polymarket.mapper import PolymarketMapper
        
        client = PolymarketLiveClient()
        mapper = PolymarketMapper()
        source = PolymarketSignalSource(client=client, mapper=mapper, logistics_only=False)

    print("OMEN Pipeline")
    print("=" * 50)
    for event in source.fetch_events(limit=args.limit):
        result = pipeline.process_single(event)
        n = len(result.signals)
        status = "cached" if result.cached else ("ok" if n else "rejected")
        print(f"  {event.event_id}: {n} signals ({status})")
    print("Done.")


if __name__ == "__main__":
    main()
