"""
Schema Router for OMEN Persistence Layer.

Determines which PostgreSQL schema (demo/live) receives a signal
based on source attestation and live gate status.

ROUTING RULES:
1. If live gate is blocked → demo schema
2. If source_type is MOCK → demo schema
3. If source_type is HYBRID → demo schema (treated as MOCK)
4. If source_type is REAL AND live gate is allowed → live schema

CRITICAL: MOCK data NEVER goes to live schema.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from ...domain.models.attestation import SignalAttestation, SourceType

logger = logging.getLogger(__name__)


class Schema(str, Enum):
    """PostgreSQL schema names."""

    DEMO = "demo"
    LIVE = "live"
    AUDIT = "audit"
    SYSTEM = "system"


class GateStatus(str, Enum):
    """Live gate status."""

    ALLOWED = "ALLOWED"  # Live mode is permitted
    BLOCKED = "BLOCKED"  # Live mode is blocked


class BlockReason(str, Enum):
    """Reasons why live gate may be blocked."""

    MASTER_SWITCH_OFF = "MASTER_SWITCH_OFF"
    INSUFFICIENT_REAL_SOURCES = "INSUFFICIENT_REAL_SOURCES"
    REQUIRED_SOURCE_MOCK = "REQUIRED_SOURCE_MOCK"
    SOURCE_UNHEALTHY = "SOURCE_UNHEALTHY"
    CONFIGURATION_ERROR = "CONFIGURATION_ERROR"


@dataclass
class GateCheckResult:
    """Result of a live gate check."""

    status: GateStatus
    block_reasons: list[BlockReason]
    real_source_count: int
    total_source_count: int
    real_source_ratio: float
    mock_sources: list[str]
    real_sources: list[str]
    checked_at: datetime

    @property
    def is_allowed(self) -> bool:
        """Check if live mode is allowed."""
        return self.status == GateStatus.ALLOWED

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "status": self.status.value,
            "block_reasons": [r.value for r in self.block_reasons],
            "real_source_count": self.real_source_count,
            "total_source_count": self.total_source_count,
            "real_source_ratio": self.real_source_ratio,
            "mock_sources": self.mock_sources,
            "real_sources": self.real_sources,
            "checked_at": self.checked_at.isoformat(),
        }


@dataclass
class RoutingDecision:
    """Result of schema routing decision."""

    schema: Schema
    attestation: SignalAttestation
    gate_status: GateStatus
    reason: str
    decided_at: datetime

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "schema": self.schema.value,
            "attestation_id": str(self.attestation.id),
            "source_type": self.attestation.source_type.value,
            "gate_status": self.gate_status.value,
            "reason": self.reason,
            "decided_at": self.decided_at.isoformat(),
        }


class SchemaRouter:
    """
    Routes signals to appropriate PostgreSQL schema based on attestation.

    Usage:
        router = SchemaRouter()

        # Route a signal
        decision = router.route(attestation, gate_result)
        schema = decision.schema  # Schema.DEMO or Schema.LIVE

        # Get table name with schema
        table = router.get_signal_table(decision)  # "demo.signals" or "live.signals"
    """

    def __init__(
        self,
        allow_live_override: Optional[bool] = None,
        min_real_ratio: Optional[float] = None,
    ):
        """
        Initialize schema router.

        Args:
            allow_live_override: Override for OMEN_ALLOW_LIVE_MODE env var
            min_real_ratio: Override for OMEN_MIN_REAL_SOURCE_RATIO env var
        """
        self._allow_live = allow_live_override
        self._min_real_ratio = min_real_ratio

    @property
    def allow_live_mode(self) -> bool:
        """Check if live mode is allowed (master switch)."""
        if self._allow_live is not None:
            return self._allow_live
        return os.environ.get("OMEN_ALLOW_LIVE_MODE", "false").lower() == "true"

    @property
    def min_real_source_ratio(self) -> float:
        """Get minimum ratio of real sources required for live mode."""
        if self._min_real_ratio is not None:
            return self._min_real_ratio
        try:
            return float(os.environ.get("OMEN_MIN_REAL_SOURCE_RATIO", "0.80"))
        except ValueError:
            return 0.80

    def route(
        self,
        attestation: SignalAttestation,
        gate_result: Optional[GateCheckResult] = None,
    ) -> RoutingDecision:
        """
        Determine which schema should receive a signal.

        Args:
            attestation: Source attestation for the signal
            gate_result: Optional pre-computed gate check result

        Returns:
            RoutingDecision with target schema and reasoning
        """
        now = datetime.now(timezone.utc)

        # If no gate result provided, assume blocked (safe default)
        gate_status = gate_result.status if gate_result else GateStatus.BLOCKED

        # Rule 1: If live gate is blocked, always route to demo
        if gate_status == GateStatus.BLOCKED:
            reason = "Live gate is BLOCKED - routing to demo schema"
            logger.debug(
                "Routing signal %s to demo (gate blocked)",
                attestation.signal_id,
            )
            return RoutingDecision(
                schema=Schema.DEMO,
                attestation=attestation,
                gate_status=gate_status,
                reason=reason,
                decided_at=now,
            )

        # Rule 2: MOCK signals always go to demo
        if attestation.source_type == SourceType.MOCK:
            reason = f"Source type is MOCK ({attestation.source_id}) - routing to demo schema"
            logger.debug(
                "Routing signal %s to demo (MOCK source)",
                attestation.signal_id,
            )
            return RoutingDecision(
                schema=Schema.DEMO,
                attestation=attestation,
                gate_status=gate_status,
                reason=reason,
                decided_at=now,
            )

        # Rule 3: HYBRID signals go to demo (treated as MOCK for routing)
        if attestation.source_type == SourceType.HYBRID:
            reason = "Source type is HYBRID (mixed inputs) - routing to demo schema"
            logger.debug(
                "Routing signal %s to demo (HYBRID source)",
                attestation.signal_id,
            )
            return RoutingDecision(
                schema=Schema.DEMO,
                attestation=attestation,
                gate_status=gate_status,
                reason=reason,
                decided_at=now,
            )

        # Rule 4: REAL signals with allowed gate go to live
        if attestation.source_type == SourceType.REAL and gate_status == GateStatus.ALLOWED:
            # Extra validation: REAL must have api_response_hash
            if not attestation.api_response_hash:
                reason = "REAL attestation missing api_response_hash - routing to demo schema"
                logger.warning(
                    "REAL signal %s missing api_response_hash, routing to demo",
                    attestation.signal_id,
                )
                return RoutingDecision(
                    schema=Schema.DEMO,
                    attestation=attestation,
                    gate_status=gate_status,
                    reason=reason,
                    decided_at=now,
                )

            reason = f"REAL source ({attestation.source_id}) with live gate ALLOWED - routing to live schema"
            logger.info(
                "Routing signal %s to LIVE schema (REAL source, gate allowed)",
                attestation.signal_id,
            )
            return RoutingDecision(
                schema=Schema.LIVE,
                attestation=attestation,
                gate_status=gate_status,
                reason=reason,
                decided_at=now,
            )

        # Fallback: route to demo (should not reach here)
        reason = "Fallback routing - demo schema"
        logger.warning(
            "Unexpected routing fallback for signal %s (source_type=%s, gate=%s)",
            attestation.signal_id,
            attestation.source_type,
            gate_status,
        )
        return RoutingDecision(
            schema=Schema.DEMO,
            attestation=attestation,
            gate_status=gate_status,
            reason=reason,
            decided_at=now,
        )

    def get_signal_table(self, decision: RoutingDecision) -> str:
        """
        Get fully qualified table name for signals.

        Args:
            decision: Routing decision

        Returns:
            Table name with schema prefix (e.g., "demo.signals")
        """
        return f"{decision.schema.value}.signals"

    def get_raw_inputs_table(self, decision: RoutingDecision) -> str:
        """Get fully qualified table name for raw inputs."""
        return f"{decision.schema.value}.raw_inputs"

    def get_ingestion_logs_table(self, decision: RoutingDecision) -> str:
        """Get fully qualified table name for ingestion logs."""
        return f"{decision.schema.value}.ingestion_logs"


def determine_schema(
    attestation: SignalAttestation,
    live_gate_allowed: bool = False,
) -> str:
    """
    Convenience function to determine schema from attestation.

    This is a simplified version for quick lookups.
    For full routing with audit trail, use SchemaRouter.route().

    Args:
        attestation: Source attestation for the signal
        live_gate_allowed: Whether live mode is currently allowed

    Returns:
        Schema name: "demo" or "live"
    """
    if not live_gate_allowed:
        return "demo"

    if attestation.source_type == SourceType.MOCK:
        return "demo"

    if attestation.source_type == SourceType.HYBRID:
        return "demo"

    if attestation.source_type == SourceType.REAL:
        # Extra check: REAL must have hash
        if attestation.api_response_hash:
            return "live"
        return "demo"

    return "demo"
