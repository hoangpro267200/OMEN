"""Seed test data for development/testing."""

import asyncio
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from omen.adapters.persistence.in_memory_repository import InMemorySignalRepository
from omen.domain.models.common import (
    GeographicRegion,
    ImpactCategory,
    ImpactSeverity,
    SignalSource,
    SignalType,
)
from omen.domain.models.explanation import ExplanationChain, ExplanationStep, StepType
from omen.domain.models.omen_signal import OMENSignal


async def seed_data():
    """Seed repository with test OMEN signals."""
    repository = InMemorySignalRepository()

    # Create sample signals
    signals = [
        OMENSignal(
            id="seed-1",
            source=SignalSource.POLYMARKET,
            signal_type=SignalType.LOGISTICS,
            timestamp=datetime.utcnow() - timedelta(hours=2),
            content="Red Sea shipping disruption: Houthi attacks force vessels to divert around Africa",
            geographic_regions=[GeographicRegion.RED_SEA],
            impact_categories=[
                ImpactCategory.ROUTE_DIVERSION,
                ImpactCategory.SHIPPING_DELAYS,
                ImpactCategory.COST_INCREASE,
            ],
            severity=ImpactSeverity.HIGH,
            confidence=0.85,
            explanation=ExplanationChain(
                steps=[
                    ExplanationStep(
                        step_type=StepType.VALIDATION,
                        rule_name="geographic_relevance",
                        description="Checked geographic relevance",
                        result="passed",
                        confidence=0.9,
                    ),
                    ExplanationStep(
                        step_type=StepType.TRANSLATION,
                        rule_name="red_sea_disruption",
                        description="Translated Red Sea disruption signal",
                        result="Identified 3 impact categories with high severity",
                        confidence=0.85,
                    ),
                ],
                total_confidence=0.85,
            ),
            source_id="poly-123",
        ),
        OMENSignal(
            id="seed-2",
            source=SignalSource.POLYMARKET,
            signal_type=SignalType.LOGISTICS,
            timestamp=datetime.utcnow() - timedelta(hours=1),
            content="Major port closure in Mediterranean due to labor strike",
            geographic_regions=[GeographicRegion.MEDITERRANEAN],
            impact_categories=[
                ImpactCategory.PORT_CLOSURE,
                ImpactCategory.SHIPPING_DELAYS,
                ImpactCategory.CAPACITY_REDUCTION,
            ],
            severity=ImpactSeverity.CRITICAL,
            confidence=0.78,
            explanation=ExplanationChain(
                steps=[
                    ExplanationStep(
                        step_type=StepType.VALIDATION,
                        rule_name="semantic_relevance",
                        description="Checked semantic relevance",
                        result="passed",
                        confidence=0.8,
                    ),
                    ExplanationStep(
                        step_type=StepType.TRANSLATION,
                        rule_name="port_closure",
                        description="Translated port closure signal",
                        result="Identified 3 impact categories with critical severity",
                        confidence=0.78,
                    ),
                ],
                total_confidence=0.78,
            ),
            source_id="poly-124",
        ),
    ]

    # Save signals
    for signal in signals:
        await repository.save_omen_signal(signal)
        print(f"Seeded signal: {signal.id} - {signal.severity.value} severity")

    print(f"\nSeeded {len(signals)} test signals")


if __name__ == "__main__":
    asyncio.run(seed_data())
