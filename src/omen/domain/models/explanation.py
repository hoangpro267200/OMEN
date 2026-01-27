"""Explainability primitives for OMEN.

Every OMEN output must be explainable. If a signal cannot be explained,
it must not be emitted.
"""

from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field

from .context import ProcessingContext


class ParameterReference(BaseModel):
    """Reference to a parameter used in a rule."""

    name: str
    value: Any
    unit: str
    source: str | None = None

    model_config = {"frozen": True}


class ExplanationStep(BaseModel):
    """
    A single step in the reasoning chain.

    Enhanced format for auditability:
    - Structured input/output
    - Parameter tracking
    - Human- and machine-readable
    Timestamp is explicit, not defaulted to utcnow().
    """

    step_id: int = Field(..., ge=1)
    rule_name: str = Field(..., description="Name of the rule/logic applied")
    rule_version: str = Field(..., description="Version of the rule")
    input_summary: dict[str, Any] = Field(
        default_factory=dict,
        description="Key inputs consumed by this step",
    )
    output_summary: dict[str, Any] = Field(
        default_factory=dict,
        description="Key outputs produced by this step",
    )
    parameters_used: list[ParameterReference] = Field(
        default_factory=list,
        description="Parameters used (with sources)",
    )
    reasoning: str = Field(..., description="Human-readable explanation")
    reasoning_template: str | None = Field(
        None,
        description="Template used to generate reasoning",
    )
    confidence_contribution: float = Field(
        ...,
        ge=0,
        le=1,
        description="How much this step contributes to overall confidence",
    )
    confidence_factors: dict[str, float] = Field(
        default_factory=dict,
        description="Breakdown of confidence contributors for this step",
    )
    timestamp: datetime = Field(..., description="Must be from ProcessingContext")
    duration_ms: float | None = Field(None, description="Step execution time in milliseconds")

    @classmethod
    def create(
        cls,
        step_id: int,
        rule_name: str,
        rule_version: str,
        reasoning: str,
        confidence_contribution: float,
        processing_time: datetime,
        input_summary: dict[str, Any] | None = None,
        output_summary: dict[str, Any] | None = None,
    ) -> "ExplanationStep":
        """Factory ensuring timestamp comes from ProcessingContext."""
        return cls(
            step_id=step_id,
            rule_name=rule_name,
            rule_version=rule_version,
            input_summary=input_summary or {},
            output_summary=output_summary or {},
            reasoning=reasoning,
            confidence_contribution=confidence_contribution,
            timestamp=processing_time,
        )

    def to_human_readable(self) -> str:
        """Generate human-readable explanation."""
        lines = [
            f"Step {self.step_id}: {self.rule_name} (v{self.rule_version})",
            f"  {self.reasoning}",
        ]
        if self.parameters_used:
            lines.append("  Parameters:")
            for param in self.parameters_used:
                lines.append(f"    - {param.name}: {param.value} {param.unit}")
                if param.source:
                    lines.append(f"      Source: {param.source}")
        lines.append(f"  Confidence contribution: {self.confidence_contribution:.0%}")
        return "\n".join(lines)

    def to_audit_format(self) -> dict:
        """Generate audit-friendly format."""
        return {
            "step_id": self.step_id,
            "rule": f"{self.rule_name}@{self.rule_version}",
            "inputs": self.input_summary,
            "outputs": self.output_summary,
            "parameters": [p.model_dump() for p in self.parameters_used],
            "reasoning": self.reasoning,
            "confidence": self.confidence_contribution,
            "timestamp": self.timestamp.isoformat(),
        }

    model_config = {"frozen": True}


class ExplanationChain(BaseModel):
    """
    Complete reasoning trace from input to output.

    All timestamps derive from ProcessingContext.
    Enables full auditability and reproducibility.
    """

    trace_id: str = Field(..., description="Unique identifier for this trace")
    steps: list[ExplanationStep] = Field(default_factory=list)
    total_steps: int = Field(default=0)
    started_at: datetime = Field(..., description="Must be from ProcessingContext")
    completed_at: datetime | None = None

    @classmethod
    def create(cls, context: ProcessingContext) -> "ExplanationChain":
        """Create chain from ProcessingContext."""
        return cls(
            trace_id=context.trace_id,
            steps=[],
            total_steps=0,
            started_at=context.processing_time,
        )

    def add_step(self, step: ExplanationStep) -> "ExplanationChain":
        """Immutable step addition."""
        new_steps = [*self.steps, step]
        return self.model_copy(
            update={"steps": new_steps, "total_steps": len(new_steps)}
        )

    def finalize(self, context: ProcessingContext) -> "ExplanationChain":
        """Mark chain as complete using context time."""
        return self.model_copy(update={"completed_at": context.processing_time})

    @property
    def summary(self) -> str:
        """Generate human-readable summary of the chain."""
        if not self.steps:
            return "No reasoning steps recorded."
        return " → ".join(s.rule_name for s in self.steps)
