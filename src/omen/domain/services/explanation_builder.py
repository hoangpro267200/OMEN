"""
Fluent builder for creating consistent explanations.
"""

from datetime import datetime
from typing import Any

from omen.domain.models.context import ProcessingContext
from omen.domain.models.explanation import (
    ExplanationChain,
    ExplanationStep,
    ParameterReference,
)


class ExplanationBuilder:
    """
    Fluent builder for ExplanationStep.

    Usage:
        step = (ExplanationBuilder(context)
            .for_rule("red_sea_disruption", "2.0.0")
            .with_input("probability", 0.75)
            .with_output("transit_increase", 7.5, "days")
            .used_parameter("reroute_transit_days", 10, "days", source="Drewry 2024")
            .with_reasoning("Red Sea disruption at {probability:.0%} adds {transit_increase} days transit")
            .with_confidence(0.8)
            .build())
    """

    def __init__(self, context: ProcessingContext, step_id: int = 1) -> None:
        self._context = context
        self._step_id = step_id
        self._rule_name: str | None = None
        self._rule_version: str | None = None
        self._inputs: dict[str, Any] = {}
        self._outputs: dict[str, Any] = {}
        self._parameters: list[ParameterReference] = []
        self._reasoning: str | None = None
        self._reasoning_template: str | None = None
        self._confidence: float = 0.5
        self._confidence_factors: dict[str, float] = {}
        self._start_time = context.processing_time

    def for_rule(self, name: str, version: str) -> "ExplanationBuilder":
        self._rule_name = name
        self._rule_version = version
        return self

    def with_input(self, name: str, value: Any) -> "ExplanationBuilder":
        self._inputs[name] = value
        return self

    def with_inputs(self, **kwargs: Any) -> "ExplanationBuilder":
        self._inputs.update(kwargs)
        return self

    def with_output(
        self, name: str, value: Any, unit: str | None = None
    ) -> "ExplanationBuilder":
        self._outputs[name] = (
            {"value": value, "unit": unit} if unit else value
        )
        return self

    def with_outputs(self, **kwargs: Any) -> "ExplanationBuilder":
        self._outputs.update(kwargs)
        return self

    def used_parameter(
        self,
        name: str,
        value: Any,
        unit: str,
        source: str | None = None,
    ) -> "ExplanationBuilder":
        self._parameters.append(
            ParameterReference(name=name, value=value, unit=unit, source=source)
        )
        return self

    def with_reasoning(self, template: str) -> "ExplanationBuilder":
        """
        Set reasoning template. Use {input_name} for substitution.

        Example: "Red Sea at {probability:.0%} adds {transit_increase} days"
        """
        self._reasoning_template = template
        format_vars: dict[str, Any] = {**self._inputs}
        for k, v in self._outputs.items():
            format_vars[k] = (
                v["value"] if isinstance(v, dict) and "value" in v else v
            )
        try:
            self._reasoning = template.format(**format_vars)
        except KeyError:
            self._reasoning = template
        return self

    def with_confidence(self, score: float, **factors: float) -> "ExplanationBuilder":
        self._confidence = score
        self._confidence_factors = factors
        return self

    def build(self) -> ExplanationStep:
        """Build the ExplanationStep."""
        if not self._rule_name or not self._rule_version:
            raise ValueError("Rule name and version required")
        if not self._reasoning:
            raise ValueError("Reasoning required")
        # Use context time for determinism; duration may be 0 in replay scenarios
        duration_ms = (self._context.processing_time - self._start_time).total_seconds() * 1000
        return ExplanationStep(
            step_id=self._step_id,
            rule_name=self._rule_name,
            rule_version=self._rule_version,
            input_summary=self._inputs,
            output_summary=self._outputs,
            parameters_used=self._parameters,
            reasoning=self._reasoning,
            reasoning_template=self._reasoning_template,
            confidence_contribution=self._confidence,
            confidence_factors=self._confidence_factors,
            timestamp=self._context.processing_time,
            duration_ms=duration_ms,
        )


class ChainBuilder:
    """Builder for ExplanationChain."""

    def __init__(self, context: ProcessingContext) -> None:
        self._context = context
        self._chain = ExplanationChain.create(context)
        self._step_count = 0

    def add_step(self, step: ExplanationStep) -> "ChainBuilder":
        self._chain = self._chain.add_step(step)
        return self

    def new_step(self) -> ExplanationBuilder:
        """Create builder for next step."""
        self._step_count += 1
        return ExplanationBuilder(self._context, self._step_count)

    def build(self) -> ExplanationChain:
        return self._chain.finalize(self._context)
