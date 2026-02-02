"""
Legacy impact-based signal model — DEPRECATED.

Use omen.domain.models.OmenSignal (pure signal contract) instead.
Impact assessment belongs in downstream consumers (e.g. RiskCast), not OMEN.
"""

from __future__ import annotations

import warnings
from datetime import datetime

from pydantic import BaseModel, Field, computed_field

from omen.domain.models.common import (
    EventId,
    SignalCategory,
    ImpactDomain,
    ConfidenceLevel,
    generate_deterministic_hash,
    RulesetVersion,
)
from omen.domain.models.explanation import ExplanationChain
from omen_impact.assessment import (
    ImpactAssessment,
    ImpactMetric,
    AffectedRoute,
    AffectedSystem,
)


class LegacyOmenSignal(BaseModel):
    """
    DEPRECATED: Legacy impact-based signal.

    Use OmenSignal from omen.domain.models for the pure signal contract.
    This class is retained only for backward compatibility during migration.
    """

    # === IDENTITY ===
    signal_id: str = Field(..., description="Unique OMEN signal identifier")
    event_id: EventId = Field(..., description="Source event identifier")

    # === CLASSIFICATION ===
    category: SignalCategory
    subcategory: str | None = None
    domain: ImpactDomain

    # === PROBABILITY & MOMENTUM ===
    current_probability: float = Field(..., ge=0, le=1)
    probability_momentum: str = Field(
        ...,
        description="INCREASING / DECREASING / STABLE",
    )
    probability_change_24h: float | None = Field(
        None,
        ge=-1,
        le=1,
        description="Change in probability over last 24 hours",
    )
    probability_is_fallback: bool = Field(
        default=False,
        description="True if probability came from fallback (e.g. 0.5) when market data was missing.",
    )

    # === CONFIDENCE (EXPLICIT, NOT IMPLIED) ===
    confidence_level: ConfidenceLevel
    confidence_score: float = Field(..., ge=0, le=1)
    confidence_factors: dict[str, float] = Field(
        default_factory=dict,
        description="Breakdown of confidence contributors",
    )

    # === IMPACT SUMMARY (deprecated — belongs in downstream) ===
    severity: float = Field(..., ge=0, le=1)
    severity_label: str
    key_metrics: list[ImpactMetric] = Field(default_factory=list)
    affected_routes: list[AffectedRoute] = Field(default_factory=list)
    affected_systems: list[AffectedSystem] = Field(default_factory=list)
    affected_regions: list[str] = Field(default_factory=list)

    # === TIMING ===
    expected_onset_hours: int | None = None
    expected_duration_hours: int | None = None

    # === HUMAN-READABLE EXPLANATION ===
    title: str = Field(..., description="Signal title for display")
    summary: str = Field(
        ...,
        min_length=10,
        max_length=500,
        description="Executive summary of the signal",
    )
    detailed_explanation: str = Field(
        ...,
        min_length=10,
        max_length=2000,
        description="Full explanation of reasoning",
    )
    explanation_chain: ExplanationChain = Field(
        ...,
        description="Full explanation chain (machine-readable)",
    )

    # === REPRODUCIBILITY CONTRACT ===
    input_event_hash: str = Field(
        ...,
        description="Hash of the input RawSignalEvent",
    )
    ruleset_version: RulesetVersion = Field(
        ...,
        description="Version of rules used to generate this signal",
    )
    deterministic_trace_id: str = Field(
        ...,
        description="Reproducible trace ID",
    )

    # === METADATA ===
    source_market: str = Field(..., description="Original market source")
    market_url: str | None = None
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    market_token_id: str | None = Field(
        default=None, description="Market/condition token ID for real-time price tracking."
    )
    clob_token_ids: list[str] | None = Field(
        default=None, description="CLOB token IDs for orderbook-based price updates."
    )

    model_config = {"frozen": True}

    @computed_field
    @property
    def is_actionable(self) -> bool:
        """Deprecated: actionability belongs in downstream consumers."""
        return (
            self.confidence_level in (ConfidenceLevel.HIGH, ConfidenceLevel.MEDIUM)
            and (len(self.affected_routes) > 0 or len(self.affected_systems) > 0)
            and self.severity >= 0.3
        )

    @computed_field
    @property
    def urgency(self) -> str:
        """Deprecated: urgency belongs in downstream consumers."""
        if self.expected_onset_hours is None:
            return "UNKNOWN"
        if self.expected_onset_hours <= 24 and self.severity >= 0.7:
            return "CRITICAL"
        if self.expected_onset_hours <= 72 and self.severity >= 0.5:
            return "HIGH"
        if self.expected_onset_hours <= 168:
            return "MEDIUM"
        return "LOW"

    def model_post_init(self, __context) -> None:
        warnings.warn(
            "LegacyOmenSignal is deprecated. Use OmenSignal from omen.domain.models. "
            "Impact assessment belongs in downstream consumers, not OMEN.",
            DeprecationWarning,
            stacklevel=2,
        )

    @classmethod
    def from_impact_assessment(
        cls,
        assessment: ImpactAssessment,
        ruleset_version: RulesetVersion,
        generated_at: datetime | None = None,
    ) -> "LegacyOmenSignal":
        """Build legacy signal from impact assessment. Deprecated."""
        source = assessment.source_signal
        original = source.original_event

        confidence_factors: dict[str, float] = {
            "signal_strength": source.signal_strength,
            "liquidity_score": source.liquidity_score,
            "validation_score": source.overall_validation_score,
        }
        for r in source.validation_results:
            if r.rule_name == "liquidity_validation":
                confidence_factors["liquidity_score"] = r.score
            elif r.rule_name == "geographic_relevance":
                confidence_factors["geographic_score"] = r.score
            elif r.rule_name == "semantic_relevance":
                confidence_factors["semantic_score"] = r.score
            elif r.rule_name == "anomaly_detection":
                confidence_factors["anomaly_score"] = r.score
        confidence_factors.setdefault("source_reliability_score", 0.85)
        confidence_score = (
            confidence_factors["signal_strength"]
            + confidence_factors["liquidity_score"]
            + confidence_factors["validation_score"]
        ) / 3

        momentum = "STABLE"
        prob_change = None
        if original.movement:
            momentum = original.movement.direction
            prob_change = original.movement.delta

        trace_id = generate_deterministic_hash(
            original.input_event_hash,
            ruleset_version,
            assessment.domain.value,
            "omen_signal",
        )
        gen_at = generated_at if generated_at is not None else datetime.utcnow()

        return cls(
            signal_id=f"OMEN-{trace_id[:12].upper()}",
            event_id=original.event_id,
            category=source.category,
            subcategory=source.subcategory,
            domain=assessment.domain,
            current_probability=original.probability,
            probability_momentum=momentum,
            probability_change_24h=prob_change,
            probability_is_fallback=getattr(original, "probability_is_fallback", False),
            confidence_level=ConfidenceLevel.from_score(confidence_score),
            confidence_score=confidence_score,
            confidence_factors=confidence_factors,
            severity=assessment.overall_severity,
            severity_label=assessment.severity_label,
            key_metrics=assessment.metrics,
            affected_routes=assessment.affected_routes,
            affected_systems=assessment.affected_systems,
            affected_regions=list(
                set(r.origin_region for r in assessment.affected_routes)
                | set(r.destination_region for r in assessment.affected_routes)
            ),
            expected_onset_hours=assessment.expected_onset_hours,
            expected_duration_hours=assessment.expected_duration_hours,
            title=original.title,
            summary=assessment.impact_summary,
            detailed_explanation=_build_detailed_explanation(assessment),
            explanation_chain=assessment.explanation_chain,
            input_event_hash=original.input_event_hash,
            ruleset_version=ruleset_version,
            deterministic_trace_id=trace_id,
            source_market=original.market.source,
            market_url=original.market.market_url,
            generated_at=gen_at,
            market_token_id=(
                original.market.condition_token_id
                or (original.market.clob_token_ids[0] if original.market.clob_token_ids else None)
            ),
            clob_token_ids=original.market.clob_token_ids,
        )


def _build_detailed_explanation(assessment: ImpactAssessment) -> str:
    """Build detailed explanation from assessment data."""
    lines = [assessment.impact_summary, ""]
    if assessment.assumptions:
        lines.append("Assumptions:")
        for assumption in assessment.assumptions:
            lines.append(f"  • {assumption}")
        lines.append("")
    if assessment.explanation_steps:
        lines.append("Reasoning chain:")
        for step in assessment.explanation_steps:
            lines.append(f"  {step.step_id}. {step.rule_name}: {step.reasoning}")
    return "\n".join(lines)
