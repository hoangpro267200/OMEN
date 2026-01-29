"""
Impact Assessment models.

Isolated from OMEN core. Impact assessment is a CONSUMER responsibility.
Uses omen.domain.models for ValidatedSignal, ExplanationChain, and common types.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal
from pydantic import BaseModel, Field, computed_field

from omen.domain.models.common import (
    EventId,
    ImpactDomain,
    generate_deterministic_hash,
    RulesetVersion,
)
from omen.domain.models.validated_signal import ValidatedSignal
from omen.domain.models.explanation import ExplanationChain, ExplanationStep


@dataclass(frozen=True)
class UncertaintyBounds:
    """
    Uncertainty bounds for an impact estimate.

    Represents the range of plausible values given model uncertainty.
    """
    lower: float  # 10th percentile estimate
    upper: float  # 90th percentile estimate
    confidence_interval: float = 0.8  # Default 80% CI

    def contains(self, value: float) -> bool:
        return self.lower <= value <= self.upper

    @property
    def range(self) -> float:
        return self.upper - self.lower

    @property
    def midpoint(self) -> float:
        return (self.lower + self.upper) / 2


class ImpactMetric(BaseModel):
    """
    A quantified impact metric with optional uncertainty.

    Every metric includes point estimate, optional uncertainty bounds,
    confidence, evidence basis, and methodology provenance.
    """
    name: str = Field(..., description="Metric identifier")
    value: float = Field(..., description="Point estimate")
    unit: str = Field(..., description="Unit of measurement")

    uncertainty: UncertaintyBounds | None = Field(
        None,
        description="Uncertainty bounds for this estimate",
    )
    confidence: float = Field(..., ge=0, le=1, description="Confidence in estimate")

    baseline: float | None = Field(None, description="Normal/baseline value")
    evidence_type: Literal["historical", "expert", "model", "assumption"] = Field(
        "assumption",
        description="Basis for this estimate",
    )
    evidence_source: str | None = Field(
        None,
        description="Citation or source for the estimate",
    )

    methodology_name: str | None = Field(
        None,
        description="Name of the methodology used to compute this metric",
    )
    methodology_version: str | None = Field(
        None,
        description="Version of the methodology",
    )
    calculation_inputs: dict[str, Any] | None = Field(
        None,
        description="Inputs used in the calculation for reproducibility",
    )
    calculated_at: str | None = Field(
        None,
        description="When this metric was calculated (ISO timestamp)",
    )

    sensitivity_to_probability: float = Field(
        1.0,
        ge=0,
        description="How much this metric scales with event probability (1.0 = linear)",
    )

    @property
    def change_from_baseline(self) -> float | None:
        """Calculate percentage change from baseline if available."""
        if self.baseline is None or self.baseline == 0:
            return None
        return ((self.value - self.baseline) / self.baseline) * 100

    @property
    def has_uncertainty(self) -> bool:
        return self.uncertainty is not None

    def scale_by_probability(self, probability: float) -> "ImpactMetric":
        """Create new metric scaled by probability."""
        scaled_value = self.value * (probability ** self.sensitivity_to_probability)

        scaled_uncertainty = None
        if self.uncertainty:
            scaled_uncertainty = UncertaintyBounds(
                lower=round(
                    self.uncertainty.lower * (probability ** self.sensitivity_to_probability),
                    2,
                ),
                upper=round(
                    self.uncertainty.upper * (probability ** self.sensitivity_to_probability),
                    2,
                ),
                confidence_interval=self.uncertainty.confidence_interval,
            )

        return self.model_copy(update={
            "value": scaled_value,
            "uncertainty": scaled_uncertainty,
        })

    model_config = {"frozen": True}


def create_transit_time_metric(
    days: float,
    probability: float,
    evidence_source: str | None = None,
) -> ImpactMetric:
    """Create a transit time increase metric with standard uncertainty."""
    val = round(days * probability, 1)
    return ImpactMetric(
        name="transit_time_increase",
        value=val,
        unit="days",
        uncertainty=UncertaintyBounds(
            lower=round(days * probability * 0.8, 1),
            upper=round(days * probability * 1.3, 1),
        ),
        confidence=0.75,
        baseline=0,
        evidence_type="historical" if evidence_source else "assumption",
        evidence_source=evidence_source,
        sensitivity_to_probability=1.0,
    )


def create_cost_increase_metric(
    percent: float,
    probability: float,
    metric_name: str = "cost_increase",
    evidence_source: str | None = None,
) -> ImpactMetric:
    """Create a cost increase metric with standard uncertainty."""
    val = round(percent * probability, 1)
    return ImpactMetric(
        name=metric_name,
        value=val,
        unit="percent",
        uncertainty=UncertaintyBounds(
            lower=round(percent * probability * 0.7, 1),
            upper=round(percent * probability * 1.5, 1),
        ),
        confidence=0.6,
        baseline=0,
        evidence_type="historical" if evidence_source else "assumption",
        evidence_source=evidence_source,
        sensitivity_to_probability=1.2,
    )


class AffectedRoute(BaseModel):
    """A logistics route affected by the signal."""
    route_id: str
    route_name: str = Field(..., description="Human-readable route name")
    origin_region: str
    destination_region: str
    impact_severity: float = Field(..., ge=0, le=1)
    alternative_routes: list[str] = Field(default_factory=list)
    estimated_delay_days: float | None = Field(None, description="Expected delay in days")
    delay_uncertainty: UncertaintyBounds | None = Field(None, description="Uncertainty on delay")

    model_config = {"frozen": True}


class AffectedSystem(BaseModel):
    """A system or infrastructure affected by the signal."""
    system_id: str
    system_name: str
    system_type: str = Field(..., description="e.g., 'PORT', 'CANAL', 'TERMINAL'")
    impact_severity: float = Field(..., ge=0, le=1)
    expected_duration_hours: int | None = None

    model_config = {"frozen": True}


class ImpactAssessment(BaseModel):
    """
    Translated impact of a validated signal.

    This is where belief becomes consequence. Every assessment
    must be deterministic, explainable, and reproducible.
    """
    event_id: EventId
    source_signal: ValidatedSignal

    domain: ImpactDomain

    metrics: list[ImpactMetric] = Field(default_factory=list)

    affected_routes: list[AffectedRoute] = Field(default_factory=list)
    affected_systems: list[AffectedSystem] = Field(default_factory=list)

    overall_severity: float = Field(
        ...,
        ge=0,
        le=1,
        description="0 = negligible, 1 = very high (maximum)"
    )
    severity_label: str = Field(..., description="Human-readable severity")

    expected_onset_hours: int | None = Field(
        None,
        description="Hours until impact begins"
    )
    expected_duration_hours: int | None = Field(
        None,
        description="Expected duration of impact"
    )

    explanation_steps: list[ExplanationStep] = Field(
        ...,
        min_length=1,
        description="Machine-readable reasoning chain. MUST NOT BE EMPTY."
    )
    explanation_chain: ExplanationChain

    impact_summary: str = Field(
        ...,
        min_length=10,
        max_length=1000,
        description="Plain English summary of the impact"
    )

    assumptions: list[str] = Field(
        default_factory=list,
        description="Explicit assumptions used in translation"
    )

    ruleset_version: RulesetVersion
    translation_rules_applied: list[str] = Field(default_factory=list)
    assessed_at: datetime = Field(default_factory=datetime.utcnow)

    is_fallback: bool = Field(
        default=False,
        description="True if no specific translation rule matched; assessment from generic fallback.",
    )
    requires_review: bool = Field(
        default=False,
        description="True when no specific impact model matched; evidence may be limited.",
    )
    fallback_reason: str | None = Field(
        default=None,
        description="Reason fallback was used, when is_fallback=True.",
    )

    @computed_field
    @property
    def deterministic_trace_id(self) -> str:
        """Reproducibility trace."""
        return generate_deterministic_hash(
            self.source_signal.deterministic_trace_id,
            self.ruleset_version,
            self.domain.value,
            "impact"
        )

    @computed_field
    @property
    def has_route_impact(self) -> bool:
        return len(self.affected_routes) > 0

    @computed_field
    @property
    def has_system_impact(self) -> bool:
        return len(self.affected_systems) > 0

    model_config = {"frozen": True}
