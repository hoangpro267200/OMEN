"""
Partner Signal Engine - Vietnamese Logistics Financial Monitor.

Monitors financial health of key Vietnamese logistics companies
to emit SIGNALS (not decisions) for counterparty risk analysis.

Target companies:
- GMD: Gemadept Corporation (Port operator)
- HAH: Hai An Transport (Shipping line)
- VOS: Vietnam Ocean Shipping (Shipping line)
- VSC: Vietnam Container Shipping (Container shipping)
- PVT: PetroVietnam Transportation (Tanker fleet)

⚠️ IMPORTANT: OMEN is a Signal Engine, NOT a Decision Engine.
This module emits signals, evidence, and confidence scores.
Risk decisions (SAFE/WARNING/CRITICAL) should be made by RiskCast.
"""

# New signal-based classes (USE THESE)
from omen.adapters.inbound.partner_risk.models import (
    PartnerSignalMetrics,
    PartnerSignalConfidence,
    PartnerSignalEvidence,
    PartnerSignalResponse,
    PartnerSignalsListResponse,
)

from omen.adapters.inbound.partner_risk.monitor import (
    LogisticsSignalMonitor,
    PartnerSignalCalculator,
    EvidenceBuilder,
    ConfidenceCalculator,
    LOGISTICS_COMPANIES,
    get_partner_signals,
    get_all_partner_signals,
)

# Deprecated classes (for backward compatibility only)
from omen.adapters.inbound.partner_risk.monitor import (
    LogisticsFinancialMonitor,  # Alias for LogisticsSignalMonitor
    RiskLevel,  # DEPRECATED - will be removed
    PartnerRiskAssessment,  # DEPRECATED - use PartnerSignalResponse
)

__all__ = [
    # New signal-based exports (USE THESE)
    "LogisticsSignalMonitor",
    "PartnerSignalCalculator",
    "EvidenceBuilder",
    "ConfidenceCalculator",
    "PartnerSignalMetrics",
    "PartnerSignalConfidence",
    "PartnerSignalEvidence",
    "PartnerSignalResponse",
    "PartnerSignalsListResponse",
    "LOGISTICS_COMPANIES",
    "get_partner_signals",
    "get_all_partner_signals",
    # Deprecated exports (for backward compatibility)
    "LogisticsFinancialMonitor",  # Alias
    "RiskLevel",  # DEPRECATED
    "PartnerRiskAssessment",  # DEPRECATED
]
