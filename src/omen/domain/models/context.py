"""
Processing context for deterministic execution.

All timestamps and IDs derive from this context.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import NewType

from .common import generate_deterministic_hash, RulesetVersion


TraceId = NewType("TraceId", str)


@dataclass(frozen=True)
class ProcessingContext:
    """
    Immutable context for a single pipeline run.

    All timestamps in the output should derive from this context,
    ensuring deterministic replay.
    """

    processing_time: datetime
    ruleset_version: RulesetVersion
    trace_id: TraceId

    @classmethod
    def create(cls, ruleset_version: RulesetVersion) -> "ProcessingContext":
        """Create a new context with current time from TimeProvider."""
        from omen.application.ports.time_provider import utc_now
        now = utc_now()
        trace_id = TraceId(
            generate_deterministic_hash(now.isoformat(), ruleset_version)
        )
        return cls(
            processing_time=now,
            ruleset_version=ruleset_version,
            trace_id=trace_id,
        )

    @classmethod
    def create_for_replay(
        cls,
        processing_time: datetime,
        ruleset_version: RulesetVersion,
    ) -> "ProcessingContext":
        """Create a context for replaying historical processing."""
        # Ensure timezone-aware datetime
        if processing_time.tzinfo is None:
            processing_time = processing_time.replace(tzinfo=timezone.utc)
        
        trace_id = TraceId(
            generate_deterministic_hash(
                processing_time.isoformat(),
                ruleset_version,
            )
        )
        return cls(
            processing_time=processing_time,
            ruleset_version=ruleset_version,
            trace_id=trace_id,
        )
