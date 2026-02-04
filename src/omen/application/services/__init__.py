"""
Application Services.

Services that orchestrate business logic across domain models and infrastructure.
"""

from omen.application.services.live_gate_service import (
    LiveGateService,
    GateDecision,
    BlockReason,
    GateCheckResult,
    get_live_gate_service,
)
from omen.application.services.gate_config import (
    GateConfig,
    get_gate_config,
)
from omen.application.services.cross_source_orchestrator import (
    CrossSourceOrchestrator,
    CrossSourceCorrelationResult,
    CorrelatedAssetData,
    correlate_signal,
)

__all__ = [
    # Gate services
    "LiveGateService",
    "GateDecision",
    "BlockReason",
    "GateCheckResult",
    "get_live_gate_service",
    "GateConfig",
    "get_gate_config",
    # Cross-source orchestration
    "CrossSourceOrchestrator",
    "CrossSourceCorrelationResult",
    "CorrelatedAssetData",
    "correlate_signal",
]
