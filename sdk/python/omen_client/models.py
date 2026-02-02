"""
OMEN SDK Data Models.

Type-safe Pydantic models for OMEN API responses.
All models are immutable (frozen=True) for thread safety.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class SignalType(str, Enum):
    """Signal type enumeration."""
    PREDICTION_MARKET = "prediction_market"
    NEWS = "news"
    COMMODITY = "commodity"
    WEATHER = "weather"
    AIS = "ais"
    STOCK = "stock"


class ConfidenceLevel(str, Enum):
    """Confidence level enumeration."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class PartnerSignalMetrics(BaseModel):
    """
    Raw signal metrics for a partner - NO VERDICT.
    
    OMEN provides metrics only. Risk decisions are made by
    downstream systems (RiskCast) based on business context.
    """
    
    model_config = ConfigDict(frozen=True)
    
    # Price signals
    price_current: Optional[float] = Field(
        None, description="Current price (x1000 VND)"
    )
    price_open: Optional[float] = None
    price_high: Optional[float] = None
    price_low: Optional[float] = None
    price_close_previous: Optional[float] = None
    price_change_percent: Optional[float] = Field(
        None, description="% change vs previous close"
    )
    price_change_absolute: Optional[float] = None
    
    # Volume signals
    volume: Optional[int] = None
    volume_avg_20d: Optional[float] = None
    volume_ratio: Optional[float] = Field(
        None, description="volume / avg_20d"
    )
    volume_anomaly_zscore: Optional[float] = Field(
        None, description="Z-score of volume"
    )
    
    # Volatility signals
    volatility_20d: Optional[float] = Field(
        None, description="20-day volatility (std dev)"
    )
    volatility_percentile: Optional[float] = Field(
        None, description="Volatility vs historical"
    )
    
    # Trend signals
    trend_1d: Optional[float] = Field(None, description="% change 1 day")
    trend_7d: Optional[float] = Field(None, description="% change 7 days")
    trend_30d: Optional[float] = Field(None, description="% change 30 days")
    trend_ytd: Optional[float] = Field(None, description="% change YTD")
    
    # Fundamental signals
    pe_ratio: Optional[float] = None
    pb_ratio: Optional[float] = None
    roe: Optional[float] = None
    roa: Optional[float] = None
    debt_to_equity: Optional[float] = None
    market_cap: Optional[float] = None
    
    # Position signals
    distance_from_52w_high: Optional[float] = Field(
        None, description="% from 52-week high"
    )
    distance_from_52w_low: Optional[float] = Field(
        None, description="% from 52-week low"
    )
    
    # Liquidity signals
    liquidity_score: Optional[float] = Field(
        None, ge=0, le=1, description="0-1, 1 = very liquid"
    )
    bid_ask_spread: Optional[float] = None


class PartnerSignalConfidence(BaseModel):
    """Confidence and data quality indicators."""
    
    model_config = ConfigDict(frozen=True)
    
    overall_confidence: float = Field(
        ..., ge=0, le=1, description="0-1 confidence score"
    )
    data_completeness: float = Field(
        ..., ge=0, le=1, description="% fields with data"
    )
    data_freshness_seconds: int = Field(
        ..., description="Age of data in seconds"
    )
    
    # Confidence breakdown
    price_data_confidence: float = Field(1.0, ge=0, le=1)
    fundamental_data_confidence: float = Field(0.0, ge=0, le=1)
    volume_data_confidence: float = Field(1.0, ge=0, le=1)
    
    # Missing data
    missing_fields: list[str] = Field(default_factory=list)
    
    # Data source info
    data_source: str = Field(..., description="vnstock, yfinance, etc.")
    data_source_reliability: float = Field(..., ge=0, le=1)


class PartnerSignalEvidence(BaseModel):
    """Evidence trail for audit."""
    
    model_config = ConfigDict(frozen=True)
    
    evidence_id: str
    evidence_type: str  # PRICE_CHANGE, VOLUME_SPIKE, etc.
    title: str
    description: Optional[str] = None
    raw_value: float
    normalized_value: float = Field(..., ge=0, le=1)
    threshold_reference: Optional[float] = None
    source: str
    observed_at: datetime


class PartnerSignalResponse(BaseModel):
    """
    Main response model for partner signals.
    
    Contains:
    - Raw signal metrics (NO verdict)
    - Confidence scores
    - Evidence trail
    - Optional suggestion (with disclaimer)
    
    IMPORTANT: OMEN does NOT make risk decisions.
    Use these signals in your own risk assessment logic.
    """
    
    model_config = ConfigDict(frozen=True)
    
    # Identity
    symbol: str
    company_name: str
    sector: str = "logistics"
    exchange: str  # HOSE, HNX, UPCOM
    
    # Signals
    signals: PartnerSignalMetrics
    
    # Confidence
    confidence: PartnerSignalConfidence
    
    # Evidence
    evidence: list[PartnerSignalEvidence] = Field(default_factory=list)
    
    # Market context
    market_context: Optional[dict] = None
    
    # Optional suggestion (NOT a decision)
    omen_suggestion: Optional[str] = Field(
        None,
        description="OMEN's suggestion - NOT a decision"
    )
    suggestion_confidence: Optional[float] = Field(None, ge=0, le=1)
    suggestion_disclaimer: str = Field(
        default="This is OMEN's signal-based suggestion only. "
                "RiskCast should make final risk decision based on order context, "
                "user risk appetite, and business rules."
    )
    
    # Metadata
    signal_id: str
    timestamp: datetime
    omen_version: str = "2.0.0"
    schema_version: str = "2.0.0"


class PartnerSignalsListResponse(BaseModel):
    """Response for multiple partners."""
    
    model_config = ConfigDict(frozen=True)
    
    timestamp: datetime
    total_partners: int
    market_context: dict = Field(default_factory=dict)
    partners: list[PartnerSignalResponse]
    aggregated_metrics: dict[str, float] = Field(default_factory=dict)
    data_quality: dict = Field(default_factory=dict)


class GeographicContext(BaseModel):
    """Geographic context for signals."""
    
    model_config = ConfigDict(frozen=True)
    
    locations: list[str] = Field(default_factory=list)
    primary_region: Optional[str] = None
    affected_ports: list[str] = Field(default_factory=list)
    affected_routes: list[str] = Field(default_factory=list)


class TemporalContext(BaseModel):
    """Temporal context for signals."""
    
    model_config = ConfigDict(frozen=True)
    
    event_time: Optional[datetime] = None
    detected_time: datetime
    expected_duration_hours: Optional[float] = None


class EvidenceItem(BaseModel):
    """Evidence item for signal tracing."""
    
    model_config = ConfigDict(frozen=True)
    
    evidence_id: str
    source: str
    title: str
    description: Optional[str] = None
    url: Optional[str] = None
    timestamp: datetime


class OmenSignal(BaseModel):
    """
    Core OMEN Signal model.
    
    Represents a processed signal with full context and evidence.
    """
    
    model_config = ConfigDict(frozen=True)
    
    signal_id: str = Field(..., description="Unique signal identifier")
    source_event_id: Optional[str] = None
    trace_id: Optional[str] = None
    input_event_hash: Optional[str] = None
    
    # Content
    title: str
    description: Optional[str] = None
    
    # Probability
    probability: Optional[float] = Field(None, ge=0, le=1)
    confidence_score: Optional[float] = Field(None, ge=0, le=1)
    confidence_level: Optional[ConfidenceLevel] = None
    
    # Classification
    signal_type: Optional[SignalType] = None
    category: Optional[str] = None
    tags: list[str] = Field(default_factory=list)
    
    # Context
    geographic: Optional[GeographicContext] = None
    temporal: Optional[TemporalContext] = None
    
    # Evidence
    evidence: list[EvidenceItem] = Field(default_factory=list)
    
    # Timestamps
    created_at: datetime
    updated_at: Optional[datetime] = None
