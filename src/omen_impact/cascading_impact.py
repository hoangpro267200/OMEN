"""Cascading Impact Analysis. Models how primary impacts cascade through the supply chain."""

from dataclasses import dataclass

from omen_impact.assessment import (
    ImpactMetric,
    ImpactAssessment,
    UncertaintyBounds,
)


@dataclass
class CascadeRule:
    """A rule for how one impact cascades to another."""

    source_metric: str
    target_metric: str
    cascade_factor: float
    delay_hours: int
    confidence_decay: float = 0.8
    description: str = ""


LOGISTICS_CASCADE_RULES: list[CascadeRule] = [
    CascadeRule(
        source_metric="transit_time_increase",
        target_metric="inventory_carrying_cost_increase",
        cascade_factor=0.15,
        delay_hours=0,
        description="Longer transit requires more safety stock",
    ),
    CascadeRule(
        source_metric="transit_time_increase",
        target_metric="production_schedule_delay",
        cascade_factor=0.8,
        delay_hours=24,
        description="Transit delays propagate to production schedules",
    ),
    CascadeRule(
        source_metric="freight_rate_pressure",
        target_metric="product_cost_increase",
        cascade_factor=0.05,
        delay_hours=72,
        description="Freight costs pass through to product pricing",
    ),
    CascadeRule(
        source_metric="port_delay",
        target_metric="demurrage_cost",
        cascade_factor=25000,
        delay_hours=0,
        description="Vessel waiting charges accumulate",
    ),
]


class CascadingImpactAnalyzer:
    """Analyzes cascading effects of primary impacts."""

    def __init__(self, rules: list[CascadeRule] | None = None):
        self._rules = rules or LOGISTICS_CASCADE_RULES

    def analyze(
        self,
        assessment: ImpactAssessment,
        max_cascade_depth: int = 2,
    ) -> list[ImpactMetric]:
        """Generate cascading impact metrics."""
        cascaded_metrics: list[ImpactMetric] = []
        primary_metrics = {m.name: m for m in assessment.metrics}

        for depth in range(max_cascade_depth):
            confidence_multiplier = 0.8 ** (depth + 1)
            for rule in self._rules:
                source = primary_metrics.get(rule.source_metric)
                if not source:
                    continue
                cascaded_value = source.value * rule.cascade_factor
                unit = self._infer_unit(rule.target_metric)
                unc = None
                if source.uncertainty:
                    unc = UncertaintyBounds(
                        lower=round(cascaded_value * 0.5, 2),
                        upper=round(cascaded_value * 2.0, 2),
                    )
                conf = min(1.0, source.confidence * confidence_multiplier)
                cascaded = ImpactMetric(
                    name=f"{rule.target_metric}_L{depth + 1}",
                    value=round(cascaded_value, 2),
                    unit=unit,
                    uncertainty=unc,
                    confidence=conf,
                    baseline=None,
                    evidence_type="model",
                    evidence_source=f"Cascaded from {rule.source_metric}: {rule.description}",
                )
                cascaded_metrics.append(cascaded)

        return cascaded_metrics

    def _infer_unit(self, metric_name: str) -> str:
        if "cost" in metric_name or "price" in metric_name:
            return "USD" if "demurrage" in metric_name else "percent"
        if "delay" in metric_name or "time" in metric_name:
            return "days"
        return "units"
