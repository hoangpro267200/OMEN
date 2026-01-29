"""
API Response Models — Signal-focused (pure Signal Intelligence contract).

These are the PUBLIC contract for OMEN as a Signal Intelligence Engine.
Downstream systems (e.g. RiskCast) consume these.
No impact calculations, no recommendations, no time-horizon or high-confidence flags.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from pydantic import BaseModel, Field, field_validator

def _format_generated_at(value: datetime | str) -> str:
    """Format generated_at as ISO 8601 string (append Z for naive UTC)."""
    if hasattr(value, "isoformat"):
        s = value.isoformat()
        if getattr(value, "tzinfo", None) is None and not s.endswith("Z"):
            return s + "Z" if "T" in s else s + "T00:00:00Z"
        return s
    return str(value)


if TYPE_CHECKING:
    from omen.domain.models.omen_signal import OmenSignal


class GeographicContextResponse(BaseModel):
    """Geographic context in API response."""
    regions: list[str] = []
    chokepoints: list[str] = []


class TemporalContextResponse(BaseModel):
    """Temporal context in API response."""
    event_horizon: Optional[str] = None
    resolution_date: Optional[str] = None


class EvidenceResponse(BaseModel):
    """Evidence item in API response."""
    source: str
    source_type: str
    url: Optional[str] = None


class ImpactHintsResponse(BaseModel):
    """Routing metadata response. NOT impact data."""
    domains: list[str] = []
    direction: str = "unknown"
    affected_asset_types: list[str] = []
    keywords: list[str] = []


class SignalResponse(BaseModel):
    """
    OMEN Signal Response — The public contract.

    What downstream systems (e.g. RiskCast) consume.

    Contains:
    - Probability (from market)
    - Confidence (OMEN-computed)
    - Context (geographic, temporal)
    - Evidence chain

    Does NOT contain:
    - Impact calculations (delay days, cost, etc.)
    - Recommendations
    - Time-horizon or relevance labels
    """

    signal_id: str
    source_event_id: str

    signal_type: str = Field(
        default="UNCLASSIFIED",
        description="Signal classification"
    )
    status: str = Field(
        default="ACTIVE",
        description="Lifecycle status"
    )
    impact_hints: ImpactHintsResponse = Field(
        default_factory=ImpactHintsResponse,
        description="Routing hints for downstream"
    )

    title: str
    description: Optional[str] = None

    probability: float = Field(
        description="Probability from source market (0-1)"
    )
    probability_source: str
    probability_is_estimate: bool = False

    confidence_score: float = Field(
        description="OMEN's confidence in signal quality (0-1, rounded to 4 decimals)"
    )
    confidence_level: str  # HIGH, MEDIUM, LOW
    confidence_factors: dict[str, float] = {}

    category: str
    tags: list[str] = []

    geographic: GeographicContextResponse
    temporal: TemporalContextResponse

    evidence: list[EvidenceResponse] = []

    trace_id: str
    ruleset_version: str
    source_url: Optional[str] = None
    observed_at: Optional[str] = Field(
        default=None,
        description="When source data was observed (ISO 8601 UTC, if available)",
    )
    generated_at: str = Field(
        description="Timestamp when OMEN generated this signal (ISO 8601 UTC)"
    )
    confidence_method: Optional[str] = Field(
        default=None,
        description="Method used to calculate confidence_score",
    )

    @field_validator("confidence_score", mode="after")
    @classmethod
    def _round_confidence(cls, v: float) -> float:
        """Round confidence score to 4 decimal places for API consumers."""
        return round(v, 4)

    @classmethod
    def from_domain(cls, signal: OmenSignal) -> SignalResponse:
        """Build API response from domain OmenSignal (pure contract)."""
        s = signal
        return cls(
            signal_id=s.signal_id,
            source_event_id=s.source_event_id,
            signal_type=getattr(s.signal_type, "value", str(getattr(s, "signal_type", "UNCLASSIFIED"))),
            status=getattr(s.status, "value", str(getattr(s, "status", "ACTIVE"))),
            impact_hints=ImpactHintsResponse(
                domains=[getattr(d, "value", str(d)) for d in (s.impact_hints.domains if hasattr(s, "impact_hints") and s.impact_hints else [])],
                direction=str(s.impact_hints.direction.value) if hasattr(s, "impact_hints") and s.impact_hints and hasattr(s.impact_hints.direction, "value") else (str(s.impact_hints.direction) if hasattr(s, "impact_hints") and s.impact_hints else "unknown"),
                affected_asset_types=list(s.impact_hints.affected_asset_types if hasattr(s, "impact_hints") and s.impact_hints else []),
                keywords=list(s.impact_hints.keywords if hasattr(s, "impact_hints") and s.impact_hints else []),
            ) if hasattr(s, "impact_hints") and s.impact_hints else ImpactHintsResponse(),
            title=s.title,
            description=s.description,
            probability=s.probability,
            probability_source=s.probability_source,
            probability_is_estimate=s.probability_is_estimate,
            confidence_score=s.confidence_score,
            confidence_level=getattr(s.confidence_level, "value", str(s.confidence_level)),
            confidence_factors=dict(s.confidence_factors) if getattr(s, "confidence_factors", None) else {},
            category=getattr(s.category, "value", str(s.category)),
            tags=list(s.tags) if getattr(s, "tags", None) else [],
            geographic=GeographicContextResponse(
                regions=list(s.geographic.regions) if s.geographic.regions else [],
                chokepoints=list(s.geographic.chokepoints) if s.geographic.chokepoints else [],
            ),
            temporal=TemporalContextResponse(
                event_horizon=str(s.temporal.event_horizon) if getattr(s.temporal, "event_horizon", None) else None,
                resolution_date=s.temporal.resolution_date.isoformat() if getattr(s.temporal, "resolution_date", None) else None,
            ),
            evidence=[
                EvidenceResponse(source=e.source, source_type=e.source_type, url=getattr(e, "url", None))
                for e in (getattr(s, "evidence", None) or [])
            ],
            trace_id=s.trace_id,
            ruleset_version=str(s.ruleset_version) if getattr(s, "ruleset_version", None) else "1.0.0",
            source_url=getattr(s, "source_url", None),
            observed_at=_format_generated_at(getattr(s, "observed_at", None)) if getattr(s, "observed_at", None) else None,
            generated_at=_format_generated_at(s.generated_at),
            confidence_method=getattr(s, "confidence_method", None),
        )


class SignalListResponse(BaseModel):
    """Response for list of signals (e.g. from /signals/process)."""
    signals: list[SignalResponse]
    total: int

    processed: int
    passed: int
    rejected: int
    pass_rate: float


class PipelineStatsResponse(BaseModel):
    """Pipeline statistics (e.g. from /signals/stats)."""
    total_processed: int
    total_passed: int
    total_rejected: int
    pass_rate: float
    rejection_by_stage: dict[str, int]

    latency_ms: float = 0
    uptime_seconds: int = 0
