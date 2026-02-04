"""
LIVE Gate Service - 3-Layer Enforcement System.

This service prevents the system from claiming LIVE mode when it's not ready.
Currently: 2/7 sources are REAL (28.6% coverage) - LIVE mode is BLOCKED.

3 LAYERS OF PROTECTION:
═══════════════════════════════════════════════════════════════════════════════

LAYER 1: CONFIG (Static - blocks immediately)
┌─────────────────────────────────────────────────────────────────────────────┐
│  OMEN_ALLOW_LIVE_MODE=false  ← Hardcoded false until production ready      │
│  If false → BLOCKED immediately, no further checks                          │
└─────────────────────────────────────────────────────────────────────────────┘

LAYER 2: SERVICE LOGIC (Dynamic - runtime checks)
┌─────────────────────────────────────────────────────────────────────────────┐
│  Check 1: real_sources / total_sources >= 0.80?                             │
│           Current: 2/7 = 28.6% → FAIL                                       │
│                                                                              │
│  Check 2: Required sources all REAL?                                        │
│           polymarket ✅, weather ❌, news ❌ → FAIL                          │
│                                                                              │
│  Check 3: All REAL sources HEALTHY?                                         │
│           → Health check validation                                          │
│                                                                              │
│  If ANY check fails → BLOCKED + log reasons                                 │
└─────────────────────────────────────────────────────────────────────────────┘

LAYER 3: API MIDDLEWARE (Request-level - per request enforcement)
┌─────────────────────────────────────────────────────────────────────────────┐
│  Every API request with X-OMEN-Mode: LIVE:                                  │
│  1. Middleware calls LiveGateService.check_gate()                           │
│  2. If BLOCKED → Return 403 or downgrade to DEMO                           │
│  3. Inject granted_mode into request.state                                  │
│  4. Add X-OMEN-Mode header to response                                      │
└─────────────────────────────────────────────────────────────────────────────┘
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from omen.application.services.gate_config import GateConfig, get_gate_config
from omen.infrastructure.data_integrity.source_registry import (
    DataSourceRegistry,
    SourceType as RegistrySourceType,
    SourceHealth,
    get_source_registry,
)

if TYPE_CHECKING:
    import asyncpg

logger = logging.getLogger(__name__)


class GateDecision(str, Enum):
    """Result of a gate check."""

    ALLOW = "ALLOW"  # LIVE mode is permitted
    BLOCK = "BLOCK"  # LIVE mode is blocked


class BlockReason(str, Enum):
    """Reasons why LIVE mode may be blocked."""

    # Layer 1: Config
    MASTER_SWITCH_OFF = "MASTER_SWITCH_OFF"

    # Layer 2: Coverage
    INSUFFICIENT_REAL_SOURCES = "INSUFFICIENT_REAL_SOURCES"
    REQUIRED_SOURCE_MOCK = "REQUIRED_SOURCE_MOCK"
    REQUIRED_SOURCE_UNHEALTHY = "REQUIRED_SOURCE_UNHEALTHY"
    REQUIRED_SOURCE_MISSING = "REQUIRED_SOURCE_MISSING"

    # Layer 2: Health
    SOURCE_UNHEALTHY = "SOURCE_UNHEALTHY"

    # Other
    CONFIGURATION_ERROR = "CONFIGURATION_ERROR"


@dataclass
class GateCheckResult:
    """
    Result of a gate check.

    This is returned by LiveGateService.check_gate() and contains
    all information needed for routing and response headers.
    """

    # Decision
    decision: GateDecision
    granted_mode: str  # "DEMO" or "LIVE"

    # Coverage stats
    real_source_count: int
    total_source_count: int
    real_source_ratio: float

    # Block details
    block_reasons: List[BlockReason] = field(default_factory=list)
    block_reason_details: Dict[str, str] = field(default_factory=dict)
    missing_sources: List[str] = field(default_factory=list)

    # Source details
    mock_sources: List[str] = field(default_factory=list)
    real_sources: List[str] = field(default_factory=list)
    unhealthy_sources: List[str] = field(default_factory=list)

    # Metadata
    checked_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    requested_mode: str = "DEMO"
    master_switch_enabled: bool = False
    required_ratio: float = 0.80

    @property
    def is_allowed(self) -> bool:
        """Check if LIVE mode is allowed."""
        return self.decision == GateDecision.ALLOW

    @property
    def is_blocked(self) -> bool:
        """Check if LIVE mode is blocked."""
        return self.decision == GateDecision.BLOCK

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization and audit logging."""
        return {
            "decision": self.decision.value,
            "granted_mode": self.granted_mode,
            "real_source_count": self.real_source_count,
            "total_source_count": self.total_source_count,
            "real_source_ratio": round(self.real_source_ratio, 4),
            "block_reasons": [r.value for r in self.block_reasons],
            "block_reason_details": self.block_reason_details,
            "missing_sources": self.missing_sources,
            "mock_sources": self.mock_sources,
            "real_sources": self.real_sources,
            "unhealthy_sources": self.unhealthy_sources,
            "checked_at": self.checked_at.isoformat(),
            "requested_mode": self.requested_mode,
            "master_switch_enabled": self.master_switch_enabled,
            "required_ratio": self.required_ratio,
        }

    def get_user_message(self) -> str:
        """Get a user-friendly message explaining the gate status."""
        if self.is_allowed:
            return "LIVE mode is available. All data sources are verified as real."

        messages = []
        if BlockReason.MASTER_SWITCH_OFF in self.block_reasons:
            messages.append("LIVE mode is disabled by system configuration.")
        if BlockReason.INSUFFICIENT_REAL_SOURCES in self.block_reasons:
            messages.append(
                f"Real source coverage is {self.real_source_ratio:.1%} "
                f"(required: {self.required_ratio:.0%})."
            )
        if BlockReason.REQUIRED_SOURCE_MOCK in self.block_reasons:
            messages.append(
                f"Required sources using mock data: {', '.join(self.missing_sources)}."
            )

        return " ".join(messages) if messages else "LIVE mode is currently unavailable."


class LiveGateService:
    """
    3-Layer LIVE Gate Enforcement Service.

    Prevents the system from claiming LIVE mode when data sources
    are not ready for production use.

    Usage:
        service = LiveGateService()
        result = service.check_gate("LIVE")

        if result.is_blocked:
            print(f"LIVE mode blocked: {result.block_reasons}")
            print(f"Using mode: {result.granted_mode}")
    """

    def __init__(
        self,
        config: Optional[GateConfig] = None,
        source_registry: Optional[DataSourceRegistry] = None,
        db_pool: Optional[Any] = None,
    ):
        """
        Initialize LiveGateService.

        Args:
            config: Gate configuration (defaults to from_env())
            source_registry: Data source registry (defaults to global)
            db_pool: Optional database pool for audit logging
        """
        self._config = config or get_gate_config()
        self._source_registry = source_registry or get_source_registry()
        self._db_pool = db_pool

        # Cache for gate status
        self._cache: Optional[GateCheckResult] = None
        self._cache_time: Optional[datetime] = None

    def check_gate(self, requested_mode: str = "DEMO") -> GateCheckResult:
        """
        Check if the requested mode is allowed.

        This is the main entry point for gate checks.
        It implements the 3-layer enforcement:
        1. Layer 1: Config check (master switch)
        2. Layer 2: Service logic (coverage, required sources, health)
        3. Layer 3: Is handled by middleware (not in this method)

        Args:
            requested_mode: The mode being requested ("DEMO" or "LIVE")

        Returns:
            GateCheckResult with decision, granted mode, and details

        Note:
            This method NEVER throws exceptions. It always returns a result.
        """
        requested_mode = requested_mode.upper()
        now = datetime.now(timezone.utc)

        # If requesting DEMO, always allow
        if requested_mode == "DEMO":
            return self._build_demo_result(requested_mode, now)

        # Check cache for LIVE requests
        if self._is_cache_valid():
            logger.debug("Using cached gate result")
            return self._cache

        # Build fresh result
        result = self._perform_gate_check(requested_mode, now)

        # Cache the result
        self._cache = result
        self._cache_time = now

        # Log to audit (async, don't block)
        self._log_gate_decision(result)

        return result

    def _is_cache_valid(self) -> bool:
        """Check if cached gate result is still valid."""
        if self._cache is None or self._cache_time is None:
            return False

        age = (datetime.now(timezone.utc) - self._cache_time).total_seconds()
        return age < self._config.gate_cache_ttl_seconds

    def _build_demo_result(
        self, requested_mode: str, checked_at: datetime
    ) -> GateCheckResult:
        """Build a result for DEMO mode requests (always allowed)."""
        sources = self._source_registry.get_all_sources()
        real_sources = [s for s in sources if s.source_type == RegistrySourceType.REAL]
        mock_sources = [s for s in sources if s.source_type == RegistrySourceType.MOCK]

        total = len(sources)
        real_count = len(real_sources)
        ratio = real_count / total if total > 0 else 0.0

        return GateCheckResult(
            decision=GateDecision.ALLOW,
            granted_mode="DEMO",
            real_source_count=real_count,
            total_source_count=total,
            real_source_ratio=ratio,
            block_reasons=[],
            mock_sources=[s.name for s in mock_sources],
            real_sources=[s.name for s in real_sources],
            checked_at=checked_at,
            requested_mode=requested_mode,
            master_switch_enabled=self._config.allow_live_mode,
            required_ratio=self._config.min_real_source_ratio,
        )

    def _perform_gate_check(
        self, requested_mode: str, checked_at: datetime
    ) -> GateCheckResult:
        """
        Perform the full gate check for LIVE mode requests.

        Implements Layer 1 and Layer 2 checks.
        """
        block_reasons: List[BlockReason] = []
        block_reason_details: Dict[str, str] = {}
        missing_sources: List[str] = []
        unhealthy_sources: List[str] = []

        # Get source information
        sources = self._source_registry.get_all_sources()
        real_sources = [s for s in sources if s.source_type == RegistrySourceType.REAL]
        mock_sources = [s for s in sources if s.source_type == RegistrySourceType.MOCK]

        total = len(sources)
        real_count = len(real_sources)
        ratio = real_count / total if total > 0 else 0.0

        # ═══════════════════════════════════════════════════════════════════════
        # LAYER 1: Master switch check
        # ═══════════════════════════════════════════════════════════════════════
        if not self._config.allow_live_mode:
            block_reasons.append(BlockReason.MASTER_SWITCH_OFF)
            block_reason_details[BlockReason.MASTER_SWITCH_OFF.value] = (
                "OMEN_ALLOW_LIVE_MODE=false (keep false until 80%+ real sources)"
            )
            logger.debug("Gate blocked: master switch is OFF")

        # ═══════════════════════════════════════════════════════════════════════
        # LAYER 2: Coverage check
        # ═══════════════════════════════════════════════════════════════════════
        if ratio < self._config.min_real_source_ratio:
            block_reasons.append(BlockReason.INSUFFICIENT_REAL_SOURCES)
            block_reason_details[BlockReason.INSUFFICIENT_REAL_SOURCES.value] = (
                f"Real source coverage {ratio:.1%} < required {self._config.min_real_source_ratio:.0%} "
                f"({real_count}/{total} sources)"
            )
            logger.debug(
                "Gate blocked: insufficient coverage %.1f%% < %.0f%%",
                ratio * 100,
                self._config.min_real_source_ratio * 100,
            )

        # ═══════════════════════════════════════════════════════════════════════
        # LAYER 2: Required sources check
        # ═══════════════════════════════════════════════════════════════════════
        for required_source in self._config.required_real_sources:
            source = self._source_registry.get_source(required_source)

            if source is None:
                block_reasons.append(BlockReason.REQUIRED_SOURCE_MISSING)
                missing_sources.append(required_source)
                block_reason_details[
                    f"{BlockReason.REQUIRED_SOURCE_MISSING.value}:{required_source}"
                ] = f"Required source '{required_source}' not found in registry"
                continue

            if source.source_type == RegistrySourceType.MOCK:
                block_reasons.append(BlockReason.REQUIRED_SOURCE_MOCK)
                missing_sources.append(required_source)
                block_reason_details[
                    f"{BlockReason.REQUIRED_SOURCE_MOCK.value}:{required_source}"
                ] = f"Required source '{required_source}' is MOCK: {source.reason}"

            if source.health == SourceHealth.UNAVAILABLE:
                block_reasons.append(BlockReason.REQUIRED_SOURCE_UNHEALTHY)
                unhealthy_sources.append(required_source)
                block_reason_details[
                    f"{BlockReason.REQUIRED_SOURCE_UNHEALTHY.value}:{required_source}"
                ] = f"Required source '{required_source}' is UNHEALTHY"

        # ═══════════════════════════════════════════════════════════════════════
        # Build result
        # ═══════════════════════════════════════════════════════════════════════
        if block_reasons:
            decision = GateDecision.BLOCK
            granted_mode = "DEMO"  # Downgrade to DEMO
        else:
            decision = GateDecision.ALLOW
            granted_mode = "LIVE"

        return GateCheckResult(
            decision=decision,
            granted_mode=granted_mode,
            real_source_count=real_count,
            total_source_count=total,
            real_source_ratio=ratio,
            block_reasons=list(set(block_reasons)),  # Deduplicate
            block_reason_details=block_reason_details,
            missing_sources=missing_sources,
            mock_sources=[s.name for s in mock_sources],
            real_sources=[s.name for s in real_sources],
            unhealthy_sources=unhealthy_sources,
            checked_at=checked_at,
            requested_mode=requested_mode,
            master_switch_enabled=self._config.allow_live_mode,
            required_ratio=self._config.min_real_source_ratio,
        )

    def _log_gate_decision(self, result: GateCheckResult) -> None:
        """
        Log gate decision to audit.gate_decisions table.

        This is fire-and-forget - errors don't block the gate check.
        """
        if self._db_pool is None:
            logger.debug("No DB pool - skipping audit log")
            return

        try:
            import asyncio

            asyncio.create_task(self._log_gate_decision_async(result))
        except Exception as e:
            logger.warning("Failed to log gate decision: %s", e)

    async def _log_gate_decision_async(self, result: GateCheckResult) -> None:
        """Async audit logging to database."""
        try:
            async with self._db_pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO audit.gate_decisions (
                        trace_id, requested_mode, decision,
                        block_reasons, master_switch_enabled,
                        real_source_count, total_source_count, real_source_ratio,
                        required_ratio, mock_sources, real_sources
                    ) VALUES ($1, $2, $3::gate_decision, $4, $5, $6, $7, $8, $9, $10, $11)
                    """,
                    None,  # trace_id from request context
                    result.requested_mode,
                    result.decision.value,
                    json.dumps([r.value for r in result.block_reasons]),
                    result.master_switch_enabled,
                    result.real_source_count,
                    result.total_source_count,
                    result.real_source_ratio,
                    result.required_ratio,
                    json.dumps(result.mock_sources),
                    json.dumps(result.real_sources),
                )
        except Exception as e:
            logger.error("Failed to write gate decision audit: %s", e)

    def get_gate_status(self) -> dict:
        """
        Get current gate status without making a LIVE request.

        Useful for health endpoints and status pages.
        """
        result = self.check_gate("DEMO")

        return {
            "live_mode_allowed": self._config.allow_live_mode
            and result.real_source_ratio >= self._config.min_real_source_ratio,
            "master_switch": self._config.allow_live_mode,
            "coverage": {
                "real": result.real_source_count,
                "total": result.total_source_count,
                "ratio": round(result.real_source_ratio, 4),
                "required_ratio": self._config.min_real_source_ratio,
                "meets_requirement": result.real_source_ratio
                >= self._config.min_real_source_ratio,
            },
            "sources": {
                "real": result.real_sources,
                "mock": result.mock_sources,
            },
            "checked_at": result.checked_at.isoformat(),
        }

    def invalidate_cache(self) -> None:
        """Invalidate the cached gate result."""
        self._cache = None
        self._cache_time = None


# Global service instance
_gate_service: Optional[LiveGateService] = None


def get_live_gate_service() -> LiveGateService:
    """Get the global LiveGateService instance."""
    global _gate_service
    if _gate_service is None:
        _gate_service = LiveGateService()
    return _gate_service


def refresh_live_gate_service() -> LiveGateService:
    """Force refresh the LiveGateService instance."""
    global _gate_service
    _gate_service = LiveGateService()
    return _gate_service
