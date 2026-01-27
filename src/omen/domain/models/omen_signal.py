"""Layer 4: OMEN_SIGNAL

The final, decision-grade output of OMEN.
This object is safe for downstream consumption.
"""

from datetime import datetime
from pydantic import BaseModel, Field, computed_field

from .common import (
    EventId,
    SignalCategory,
    ImpactDomain,
    ConfidenceLevel,
    generate_deterministic_hash,
    RulesetVersion
)
from .impact_assessment import (
    ImpactAssessment, 
    ImpactMetric, 
    AffectedRoute, 
    AffectedSystem
)
from .explanation import ExplanationChain


class OmenSignal(BaseModel):
    """
    Layer 4 Output: The final OMEN intelligence artifact.
    
    This is the contract between OMEN and downstream consumers.
    
    NON-NEGOTIABLE PROPERTIES:
    - Structured
    - Explainable
    - Timestamped
    - Reproducible given same inputs
    - Contains no hidden logic
    
    If a signal cannot meet these criteria, it MUST NOT be emitted.
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
        description="INCREASING / DECREASING / STABLE"
    )
    probability_change_24h: float | None = Field(
        None, 
        ge=-1, 
        le=1,
        description="Change in probability over last 24 hours"
    )
    
    # === CONFIDENCE (EXPLICIT, NOT IMPLIED) ===
    confidence_level: ConfidenceLevel
    confidence_score: float = Field(..., ge=0, le=1)
    confidence_factors: dict[str, float] = Field(
        default_factory=dict,
        description="Breakdown of confidence contributors"
    )
    
    # === IMPACT SUMMARY ===
    severity: float = Field(..., ge=0, le=1)
    severity_label: str
    key_metrics: list[ImpactMetric] = Field(default_factory=list)
    
    # === AFFECTED INFRASTRUCTURE ===
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
        description="Executive summary of the signal"
    )
    detailed_explanation: str = Field(
        ...,
        min_length=10,
        max_length=2000,
        description="Full explanation of reasoning"
    )
    
    # === FULL EXPLANATION CHAIN (MACHINE-READABLE) ===
    explanation_chain: ExplanationChain
    
    # === REPRODUCIBILITY CONTRACT ===
    input_event_hash: str = Field(
        ..., 
        description="Hash of the input RawSignalEvent"
    )
    ruleset_version: RulesetVersion = Field(
        ..., 
        description="Version of rules used to generate this signal"
    )
    deterministic_trace_id: str = Field(
        ..., 
        description="Reproducible trace ID"
    )
    
    # === METADATA ===
    source_market: str = Field(..., description="Original market source")
    market_url: str | None = None
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # === INTERNAL REFERENCES (for debugging, excluded from API) ===
    _source_assessment: ImpactAssessment | None = None
    
    @computed_field
    @property
    def is_actionable(self) -> bool:
        """
        A signal is actionable if it has:
        - HIGH or MEDIUM confidence
        - At least one affected route or system
        - Non-negligible severity
        """
        return (
            self.confidence_level in (ConfidenceLevel.HIGH, ConfidenceLevel.MEDIUM)
            and (len(self.affected_routes) > 0 or len(self.affected_systems) > 0)
            and self.severity >= 0.3
        )
    
    @computed_field
    @property
    def urgency(self) -> str:
        """Derived urgency level based on onset timing and severity."""
        if self.expected_onset_hours is None:
            return "UNKNOWN"
        if self.expected_onset_hours <= 24 and self.severity >= 0.7:
            return "CRITICAL"
        if self.expected_onset_hours <= 72 and self.severity >= 0.5:
            return "HIGH"
        if self.expected_onset_hours <= 168:  # 1 week
            return "MEDIUM"
        return "LOW"
    
    @classmethod
    def from_impact_assessment(
        cls,
        assessment: ImpactAssessment,
        ruleset_version: RulesetVersion,
        generated_at: datetime | None = None,
    ) -> "OmenSignal":
        """
        Factory method to construct OmenSignal from ImpactAssessment.

        This ensures consistent transformation from Layer 3 to Layer 4.
        Pass generated_at for deterministic replay (e.g. from ProcessingContext).
        """
        source = assessment.source_signal
        original = source.original_event

        # Calculate confidence
        confidence_factors = {
            "signal_strength": source.signal_strength,
            "liquidity_score": source.liquidity_score,
            "validation_score": source.overall_validation_score,
        }
        confidence_score = sum(confidence_factors.values()) / len(confidence_factors)

        # Determine momentum
        momentum = "STABLE"
        prob_change = None
        if original.movement:
            momentum = original.movement.direction
            prob_change = original.movement.delta

        # Build trace ID
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
            confidence_level=ConfidenceLevel.from_score(confidence_score),
            confidence_score=confidence_score,
            confidence_factors=confidence_factors,
            severity=assessment.overall_severity,
            severity_label=assessment.severity_label,
            key_metrics=assessment.metrics,
            affected_routes=assessment.affected_routes,
            affected_systems=assessment.affected_systems,
            affected_regions=list(set(
                r.origin_region for r in assessment.affected_routes
            ) | set(
                r.destination_region for r in assessment.affected_routes
            )),
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
            _source_assessment=assessment,
        )
    
    model_config = {"frozen": True}


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
