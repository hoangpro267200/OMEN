"""
Partner Signal Models - Pure Signal Engine.

These models contain ONLY raw metrics and evidence.
NO risk verdicts (SAFE/WARNING/CRITICAL) - that's RiskCast's job.

This follows OMEN's core principle: Signal Engine, not Decision Engine.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class PartnerSignalMetrics(BaseModel):
    """
    Raw signal metrics for a partner - NO VERDICT.
    RiskCast will decide risk level based on these metrics.
    """

    model_config = ConfigDict(frozen=True)  # Immutable

    # === PRICE SIGNALS ===
    price_current: Optional[float] = Field(None, description="Current price (x1000 VND)")
    price_open: Optional[float] = None
    price_high: Optional[float] = None
    price_low: Optional[float] = None
    price_close_previous: Optional[float] = None
    price_change_percent: Optional[float] = Field(None, description="% change vs previous close")
    price_change_absolute: Optional[float] = None

    # === VOLUME SIGNALS ===
    volume: Optional[int] = None
    volume_avg_20d: Optional[float] = None
    volume_ratio: Optional[float] = Field(None, description="volume / avg_20d")
    volume_anomaly_zscore: Optional[float] = Field(None, description="Z-score of volume")

    # === VOLATILITY SIGNALS ===
    volatility_20d: Optional[float] = Field(None, description="20-day volatility (std dev)")
    volatility_percentile: Optional[float] = Field(None, description="Volatility vs history")

    # === TREND SIGNALS ===
    trend_1d: Optional[float] = Field(None, description="% change 1 day")
    trend_7d: Optional[float] = Field(None, description="% change 7 days")
    trend_30d: Optional[float] = Field(None, description="% change 30 days")
    trend_ytd: Optional[float] = Field(None, description="% change YTD")

    # === FUNDAMENTAL SIGNALS (nullable - may not have data) ===
    pe_ratio: Optional[float] = None
    pb_ratio: Optional[float] = None
    roe: Optional[float] = None
    roa: Optional[float] = None
    debt_to_equity: Optional[float] = None
    current_ratio: Optional[float] = None
    market_cap: Optional[float] = None

    # === POSITION SIGNALS ===
    distance_from_52w_high: Optional[float] = Field(None, description="% from 52-week high")
    distance_from_52w_low: Optional[float] = Field(None, description="% from 52-week low")

    # === LIQUIDITY SIGNALS ===
    liquidity_score: Optional[float] = Field(None, ge=0, le=1, description="0-1, 1 = very liquid")
    bid_ask_spread: Optional[float] = None


class PartnerSignalConfidence(BaseModel):
    """Confidence and data quality indicators."""

    model_config = ConfigDict(frozen=True)

    overall_confidence: float = Field(..., ge=0, le=1, description="0-1 confidence score")
    data_completeness: float = Field(..., ge=0, le=1, description="% fields with data")
    data_freshness_seconds: int = Field(..., description="Age of data in seconds")

    # Confidence breakdown
    price_data_confidence: float = Field(1.0, ge=0, le=1)
    fundamental_data_confidence: float = Field(0.0, ge=0, le=1)
    volume_data_confidence: float = Field(1.0, ge=0, le=1)

    # Missing data list
    missing_fields: list[str] = Field(default_factory=list)

    # Data source info
    data_source: str = Field(..., description="vnstock, yfinance, etc.")
    data_source_reliability: float = Field(..., ge=0, le=1)


class PartnerSignalEvidence(BaseModel):
    """Evidence trail for audit."""

    model_config = ConfigDict(frozen=True)

    evidence_id: str
    evidence_type: str  # PRICE_CHANGE, VOLUME_SPIKE, TREND_REVERSAL, etc.
    title: str
    description: Optional[str] = None
    raw_value: float
    normalized_value: float = Field(..., ge=0, le=1)
    threshold_reference: Optional[float] = None
    source: str
    observed_at: datetime


class PartnerSignalResponse(BaseModel):
    """
    🔥 MAIN RESPONSE MODEL - Pure Signals, NO VERDICT

    OMEN sends signals + evidence + confidence.
    RiskCast decides SAFE/WARNING/CRITICAL.
    """

    model_config = ConfigDict(frozen=True)

    # === IDENTITY ===
    symbol: str
    company_name: str
    sector: str = "logistics"
    exchange: str = Field(default="HOSE", description="HOSE, HNX, UPCOM")

    # === RAW SIGNALS (normalized metrics) ===
    signals: PartnerSignalMetrics

    # === CONFIDENCE & DATA QUALITY ===
    confidence: PartnerSignalConfidence

    # === EVIDENCE TRAIL ===
    evidence: list[PartnerSignalEvidence] = Field(default_factory=list)

    # === CONTEXT FOR RISKCAST ===
    market_context: Optional[dict] = Field(None, description="VNINDEX, sector performance")

    # === OMEN SUGGESTION (optional, with disclaimer) ===
    omen_suggestion: Optional[str] = Field(
        None, description="OMEN's suggestion - NOT a decision. RiskCast must make final call."
    )
    suggestion_confidence: Optional[float] = Field(None, ge=0, le=1)
    suggestion_disclaimer: str = Field(
        default="This is OMEN's signal-based suggestion only. "
        "RiskCast should make final risk decision based on order context, "
        "user risk appetite, and business rules."
    )

    # === METADATA ===
    signal_id: str = Field(..., description="Unique signal ID for tracing")
    timestamp: datetime
    omen_version: str = "2.0.0"
    schema_version: str = "2.0.0"


class PartnerSignalsListResponse(BaseModel):
    """Response for multiple partners."""

    model_config = ConfigDict(frozen=True)

    timestamp: datetime
    total_partners: int

    # Common market context
    market_context: dict = Field(default_factory=dict)

    # Partners with signals
    partners: list[PartnerSignalResponse]

    # Aggregated metrics (NO verdict)
    aggregated_metrics: dict[str, float] = Field(
        default_factory=dict, description="Avg volatility, avg liquidity, etc. - NO risk verdict"
    )

    # Data quality summary
    data_quality: dict = Field(default_factory=dict)

    # ❌ NO these fields:
    # - overall_risk
    # - risk_breakdown
    # - risk_status


# === DEPRECATED MODELS (for backward compatibility during migration) ===


class DeprecatedRiskLevel:
    """
    ⚠️ DEPRECATED - Do not use in new code.

    This is kept only for migration purposes.
    RiskCast should implement its own risk levels.
    """

    SAFE = "SAFE"
    CAUTION = "CAUTION"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"

    @classmethod
    def from_signals(cls, signals: PartnerSignalMetrics) -> str:
        """
        ⚠️ DEPRECATED - Migration helper only.

        Convert signals to risk level. This logic should be in RiskCast.
        """
        import warnings

        warnings.warn(
            "DeprecatedRiskLevel.from_signals() is deprecated. "
            "Move risk decision logic to RiskCast.",
            DeprecationWarning,
            stacklevel=2,
        )

        # Price-based (these are just signals - RiskCast should decide)
        if signals.price_change_percent is not None:
            if signals.price_change_percent <= -7.0:
                return cls.CRITICAL
            if signals.price_change_percent <= -4.0:
                return cls.WARNING

        # ROE-based
        if signals.roe is not None:
            if signals.roe < 0:
                return cls.WARNING
            if signals.roe < 5.0:
                return cls.CAUTION

        return cls.SAFE
