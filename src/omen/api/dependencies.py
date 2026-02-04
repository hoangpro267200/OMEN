"""FastAPI dependencies."""

from functools import lru_cache

from omen.application.container import get_container
from omen.application.ports.signal_repository import SignalRepository
from omen.application.signal_pipeline import SignalOnlyPipeline
from omen.domain.models.common import RulesetVersion
from omen.domain.services.signal_enricher import SignalEnricher
from omen.domain.services.signal_validator import SignalValidator


def get_repository() -> SignalRepository:
    """Return the signal repository from the application container."""
    return get_container().repository


@lru_cache(maxsize=1)
def get_signal_only_pipeline() -> SignalOnlyPipeline:
    """Return the signal-only pipeline (validate → enrich → OmenSignal).
    
    AUDIT FIX (2026-02-03): Changed from create_default() to create_full()
    to enable all 12 validation rules instead of just 6.
    
    Rules now active:
    - Core: liquidity, anomaly, semantic, geographic (4)
    - Cross-source: CrossSourceValidationRule, SourceDiversityRule (2)
    - News: NewsQualityGateRule (1)
    - Commodity: CommodityContextRule (1)
    - AIS/Maritime: PortCongestion, ChokePointDelay, Freshness, Quality (4)
    """
    validator = SignalValidator.create_full()
    enricher = SignalEnricher()
    return SignalOnlyPipeline(
        validator=validator,
        enricher=enricher,
        ruleset_version=RulesetVersion("1.0.0"),
    )
