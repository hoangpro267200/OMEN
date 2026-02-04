"""
Gate Configuration for LIVE Mode Enforcement.

Layer 1 of the 3-layer gate system:
- Static configuration that blocks LIVE mode at the earliest point
- OMEN_ALLOW_LIVE_MODE=false prevents any LIVE mode attempt
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class GateConfig:
    """
    Configuration for the LIVE gate.

    This is Layer 1 of the 3-layer enforcement system.
    If allow_live_mode is False, LIVE mode is blocked immediately
    without any further checks.
    """

    # Master switch - if False, LIVE mode is blocked immediately
    allow_live_mode: bool = False

    # Minimum ratio of REAL sources required for LIVE mode
    min_real_source_ratio: float = 0.80

    # Sources that MUST be REAL for LIVE mode (empty = all sources)
    required_real_sources: List[str] = field(default_factory=list)

    # Cache TTL for gate status (seconds)
    gate_cache_ttl_seconds: int = 30

    @classmethod
    def from_env(cls) -> GateConfig:
        """
        Load gate configuration from environment variables.

        Environment Variables:
            OMEN_ALLOW_LIVE_MODE: Master switch (default: false)
            OMEN_MIN_REAL_SOURCE_RATIO: Minimum REAL/total ratio (default: 0.80)
            OMEN_REQUIRED_REAL_SOURCES: Comma-separated list of required sources
            OMEN_GATE_CACHE_TTL_SECONDS: Cache TTL (default: 30)
        """
        # Master switch - default to FALSE for safety
        allow_live_mode = os.environ.get("OMEN_ALLOW_LIVE_MODE", "false").lower() == "true"

        # Minimum ratio
        try:
            min_real_source_ratio = float(
                os.environ.get("OMEN_MIN_REAL_SOURCE_RATIO", "0.80")
            )
        except ValueError:
            logger.warning("Invalid OMEN_MIN_REAL_SOURCE_RATIO, using default 0.80")
            min_real_source_ratio = 0.80

        # Required sources
        required_sources_str = os.environ.get("OMEN_REQUIRED_REAL_SOURCES", "")
        if required_sources_str:
            required_real_sources = [
                s.strip() for s in required_sources_str.split(",") if s.strip()
            ]
        else:
            # Default required sources for LIVE mode
            required_real_sources = ["polymarket"]  # At minimum, polymarket must be REAL

        # Cache TTL
        try:
            gate_cache_ttl_seconds = int(
                os.environ.get("OMEN_GATE_CACHE_TTL_SECONDS", "30")
            )
        except ValueError:
            gate_cache_ttl_seconds = 30

        config = cls(
            allow_live_mode=allow_live_mode,
            min_real_source_ratio=min_real_source_ratio,
            required_real_sources=required_real_sources,
            gate_cache_ttl_seconds=gate_cache_ttl_seconds,
        )

        logger.info(
            "Gate config loaded: allow_live=%s, min_ratio=%.2f, required=%s",
            config.allow_live_mode,
            config.min_real_source_ratio,
            config.required_real_sources,
        )

        return config

    def is_master_switch_on(self) -> bool:
        """Check if the master switch allows LIVE mode."""
        return self.allow_live_mode


# Global config instance
_gate_config: Optional[GateConfig] = None


def get_gate_config() -> GateConfig:
    """Get the global gate configuration instance."""
    global _gate_config
    if _gate_config is None:
        _gate_config = GateConfig.from_env()
    return _gate_config


def refresh_gate_config() -> GateConfig:
    """Force refresh the gate configuration from environment."""
    global _gate_config
    _gate_config = GateConfig.from_env()
    return _gate_config
