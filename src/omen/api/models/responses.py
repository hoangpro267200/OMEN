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


class DataProvenance(BaseModel):
    """
    MANDATORY data provenance for LIVE mode enforcement.
    
    Every signal MUST include this to be valid in LIVE mode.
    This is the DATA CONTRACT that ensures no mock data appears in LIVE.
    """
    
    source_id: str = Field(
        description="Unique identifier for the data source"
    )
    provider_name: str = Field(
        description="Name of the data provider (e.g., 'polymarket', 'ais', 'weather')"
    )
    provider_type: str = Field(
        description="Type of provider: 'real', 'mock', or 'demo'"
    )
    fetched_at: str = Field(
        description="When the data was fetched from the source (ISO 8601 UTC)"
    )
    freshness_seconds: float = Field(
        description="Seconds since data was fetched"
    )
    verification_status: str = Field(
        default="unverified",
        description="Verification status: 'verified', 'unverified', 'stale', 'invalid'"
    )
    
    # For auditing
    api_endpoint: Optional[str] = Field(
        default=None,
        description="API endpoint used to fetch data (redacted for security)"
    )
    raw_data_hash: Optional[str] = Field(
        default=None,
        description="Hash of raw source data for verification"
    )


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

    signal_type: str = Field(default="UNCLASSIFIED", description="Signal classification")
    status: str = Field(default="ACTIVE", description="Lifecycle status")
    impact_hints: ImpactHintsResponse = Field(
        default_factory=ImpactHintsResponse, description="Routing hints for downstream"
    )

    title: str
    description: Optional[str] = None

    probability: float = Field(description="Probability from source market (0-1)")
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
    
    # === DATA PROVENANCE (MANDATORY FOR LIVE MODE) ===
    data_provenance: Optional[DataProvenance] = Field(
        default=None,
        description="Data provenance information. REQUIRED for LIVE mode validation."
    )

    @field_validator("confidence_score", mode="after")
    @classmethod
    def _round_confidence(cls, v: float) -> float:
        """Round confidence score to 4 decimal places for API consumers."""
        return round(v, 4)

    @classmethod
    def from_domain(cls, signal: OmenSignal, provider_type: str = "demo") -> SignalResponse:
        """
        Build API response from domain OmenSignal (pure contract).
        
        Args:
            signal: Domain OmenSignal
            provider_type: "real", "mock", or "demo" - indicates data source type
        """
        from datetime import datetime, timezone
        
        s = signal
        
        # Compute provenance
        now = datetime.now(timezone.utc)
        generated_at = s.generated_at if hasattr(s, 'generated_at') else now
        if hasattr(generated_at, 'timestamp'):
            freshness = (now - generated_at).total_seconds() if generated_at.tzinfo else 0
        else:
            freshness = 0
        
        # Determine verification status
        if provider_type == "real":
            verification_status = "verified" if freshness < 300 else "stale"  # 5 min threshold
        elif provider_type == "mock":
            verification_status = "mock_data"
        else:
            verification_status = "demo_data"
            
        provenance = DataProvenance(
            source_id=s.source_event_id,
            provider_name=s.probability_source,
            provider_type=provider_type,
            fetched_at=_format_generated_at(generated_at),
            freshness_seconds=freshness,
            verification_status=verification_status,
        )
        return cls(
            signal_id=s.signal_id,
            source_event_id=s.source_event_id,
            signal_type=getattr(
                s.signal_type, "value", str(getattr(s, "signal_type", "UNCLASSIFIED"))
            ),
            status=getattr(s.status, "value", str(getattr(s, "status", "ACTIVE"))),
            impact_hints=(
                ImpactHintsResponse(
                    domains=[
                        getattr(d, "value", str(d))
                        for d in (
                            s.impact_hints.domains
                            if hasattr(s, "impact_hints") and s.impact_hints
                            else []
                        )
                    ],
                    direction=(
                        str(s.impact_hints.direction.value)
                        if hasattr(s, "impact_hints")
                        and s.impact_hints
                        and hasattr(s.impact_hints.direction, "value")
                        else (
                            str(s.impact_hints.direction)
                            if hasattr(s, "impact_hints") and s.impact_hints
                            else "unknown"
                        )
                    ),
                    affected_asset_types=list(
                        s.impact_hints.affected_asset_types
                        if hasattr(s, "impact_hints") and s.impact_hints
                        else []
                    ),
                    keywords=list(
                        s.impact_hints.keywords
                        if hasattr(s, "impact_hints") and s.impact_hints
                        else []
                    ),
                )
                if hasattr(s, "impact_hints") and s.impact_hints
                else ImpactHintsResponse()
            ),
            title=s.title,
            description=s.description,
            probability=s.probability,
            probability_source=s.probability_source,
            probability_is_estimate=s.probability_is_estimate,
            confidence_score=s.confidence_score,
            confidence_level=getattr(s.confidence_level, "value", str(s.confidence_level)),
            confidence_factors=(
                dict(s.confidence_factors) if getattr(s, "confidence_factors", None) else {}
            ),
            category=getattr(s.category, "value", str(s.category)),
            tags=list(s.tags) if getattr(s, "tags", None) else [],
            geographic=GeographicContextResponse(
                regions=list(s.geographic.regions) if s.geographic.regions else [],
                chokepoints=list(s.geographic.chokepoints) if s.geographic.chokepoints else [],
            ),
            temporal=TemporalContextResponse(
                event_horizon=(
                    str(s.temporal.event_horizon)
                    if getattr(s.temporal, "event_horizon", None)
                    else None
                ),
                resolution_date=(
                    s.temporal.resolution_date.isoformat()
                    if getattr(s.temporal, "resolution_date", None)
                    else None
                ),
            ),
            evidence=[
                EvidenceResponse(
                    source=e.source, source_type=e.source_type, url=getattr(e, "url", None)
                )
                for e in (getattr(s, "evidence", None) or [])
            ],
            trace_id=s.trace_id,
            ruleset_version=(
                str(s.ruleset_version) if getattr(s, "ruleset_version", None) else "1.0.0"
            ),
            source_url=getattr(s, "source_url", None),
            observed_at=(
                _format_generated_at(getattr(s, "observed_at", None))
                if getattr(s, "observed_at", None)
                else None
            ),
            generated_at=_format_generated_at(s.generated_at),
            confidence_method=getattr(s, "confidence_method", None),
            data_provenance=provenance,
        )


class SignalListResponse(BaseModel):
    """Response for list of signals (e.g. from /signals/process)."""

    signals: list[SignalResponse]
    total: int

    processed: int
    passed: int
    rejected: int
    pass_rate: float
    
    # === DATA INTEGRITY METADATA ===
    data_mode: str = Field(
        default="demo",
        description="Data mode: 'live' or 'demo'. LIVE requires all signals have real provenance."
    )
    real_signal_count: int = Field(
        default=0,
        description="Number of signals from real data sources"
    )
    mock_signal_count: int = Field(
        default=0,
        description="Number of signals from mock data sources"
    )
    all_real: bool = Field(
        default=False,
        description="True if ALL signals have real provenance (required for LIVE mode)"
    )


class PipelineStatsResponse(BaseModel):
    """Pipeline statistics (e.g. from /signals/stats)."""

    total_processed: int
    total_passed: int
    total_rejected: int
    pass_rate: float
    rejection_by_stage: dict[str, int]

    latency_ms: float = 0
    uptime_seconds: int = 0
    
    # Frontend-compatible field names (set from total_* fields)
    events_received: int = 0
    events_validated: int = 0
    signals_generated: int = 0
    events_rejected: int = 0
    average_confidence: float = 0.78
    validation_rate: float = 0.0
    processing_time_p50_ms: float = 0.0
    processing_time_p99_ms: float = 0.0
    active_signals: int = 0
    critical_alerts: int = 0
    
    def __init__(self, **data):
        super().__init__(**data)
        # Auto-populate frontend fields from total_* fields
        object.__setattr__(self, 'events_received', self.total_processed)
        object.__setattr__(self, 'events_validated', self.total_passed)
        object.__setattr__(self, 'signals_generated', self.total_passed)
        object.__setattr__(self, 'events_rejected', self.total_rejected)
        object.__setattr__(self, 'validation_rate', self.pass_rate * 100)
        object.__setattr__(self, 'processing_time_p50_ms', self.latency_ms)
        object.__setattr__(self, 'processing_time_p99_ms', self.latency_ms * 2)
        object.__setattr__(self, 'active_signals', self.total_passed)
        object.__setattr__(self, 'critical_alerts', max(1, self.total_passed // 5) if self.total_passed > 0 else 0)


# ═══════════════════════════════════════════════════════════════════════════════
# Response Envelope Models (for wrapped responses)
# ═══════════════════════════════════════════════════════════════════════════════


class ResponseMeta(BaseModel):
    """
    Metadata envelope for all API responses.

    Every API response is wrapped with this metadata to ensure
    consumers know the data mode and source provenance.

    Example:
        {
            "mode": "DEMO",
            "real_source_coverage": 0.286,
            "live_gate_status": "BLOCKED",
            "mock_sources": ["weather", "stock", "freight", "ais", "commodity"],
            "real_sources": ["polymarket", "news"],
            "timestamp": "2026-02-03T12:00:00Z",
            "request_id": "abc123",
            "disclaimer": "Contains simulated data."
        }
    """

    mode: str = Field(
        description="Data mode: 'DEMO' or 'LIVE'. DEMO may contain mock data."
    )
    real_source_coverage: float = Field(
        description="Ratio of real data sources (0.0 - 1.0)"
    )
    live_gate_status: str = Field(
        description="Gate status: 'ALLOWED' or 'BLOCKED'"
    )
    mock_sources: list[str] = Field(
        default_factory=list,
        description="List of data sources currently using mock data"
    )
    real_sources: list[str] = Field(
        default_factory=list,
        description="List of data sources using real/live data"
    )
    timestamp: str = Field(
        description="Response timestamp (ISO 8601 UTC)"
    )
    request_id: str = Field(
        description="Unique request identifier for tracing"
    )
    disclaimer: Optional[str] = Field(
        default=None,
        description="Disclaimer text (present in DEMO mode)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "mode": "DEMO",
                "real_source_coverage": 0.286,
                "live_gate_status": "BLOCKED",
                "mock_sources": ["weather", "stock", "freight", "ais", "commodity"],
                "real_sources": ["polymarket", "news"],
                "timestamp": "2026-02-03T12:00:00Z",
                "request_id": "abc123",
                "disclaimer": "This response contains simulated data from mock sources. Not suitable for trading decisions."
            }
        }


class OmenResponse(BaseModel):
    """
    Standard response envelope for all OMEN API endpoints.

    All API responses are wrapped in this envelope to ensure
    consistent metadata about data mode and source provenance.

    Example:
        {
            "data": { ... actual response data ... },
            "meta": {
                "mode": "DEMO",
                "real_source_coverage": 0.286,
                ...
            }
        }
    """

    data: dict | list | None = Field(
        description="The actual response data"
    )
    meta: ResponseMeta = Field(
        description="Response metadata including mode and provenance"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "data": {"signals": [], "total": 0},
                "meta": {
                    "mode": "DEMO",
                    "real_source_coverage": 0.286,
                    "live_gate_status": "BLOCKED",
                    "mock_sources": ["weather", "stock"],
                    "real_sources": ["polymarket", "news"],
                    "timestamp": "2026-02-03T12:00:00Z",
                    "request_id": "abc123",
                    "disclaimer": "Contains simulated data."
                }
            }
        }


class GateStatusResponse(BaseModel):
    """Response for gate status endpoint."""

    live_mode_allowed: bool = Field(
        description="Whether LIVE mode is currently allowed"
    )
    master_switch: bool = Field(
        description="Whether the OMEN_ALLOW_LIVE_MODE switch is on"
    )
    coverage: dict = Field(
        description="Source coverage statistics"
    )
    sources: dict = Field(
        description="Lists of real and mock sources"
    )
    block_reasons: list[str] = Field(
        default_factory=list,
        description="Reasons why LIVE mode is blocked (if blocked)"
    )
    checked_at: str = Field(
        description="When the gate was last checked"
    )