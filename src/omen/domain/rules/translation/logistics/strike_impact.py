"""
Strike/Labor Disruption Translation Rule.

Translates labor/strike signals into logistics impacts.
"""

from datetime import datetime

from ....models.common import ImpactDomain, SignalCategory
from ....models.validated_signal import ValidatedSignal
from ....models.impact_assessment import (
    ImpactMetric,
    UncertaintyBounds,
    AffectedSystem,
)
from ....models.explanation import ExplanationStep
from ..base import BaseTranslationRule, TranslationResult
from .parameters import STRIKE_PARAMS, get_param


class StrikeImpactRule(BaseTranslationRule):
    """
    Translates labor/strike signals into logistics impacts.
    """

    @property
    def name(self) -> str:
        return "strike_impact_logistics"

    @property
    def version(self) -> str:
        return "2.0.0"

    @property
    def domain(self) -> ImpactDomain:
        return ImpactDomain.LOGISTICS

    @property
    def applicable_categories(self) -> set[SignalCategory]:
        return {SignalCategory.LABOR}

    @property
    def applicable_keywords(self) -> set[str]:
        return {
            "strike",
            "labor",
            "union",
            "workers",
            "walkout",
            "industrial action",
            "work stoppage",
        }

    def translate(
        self,
        signal: ValidatedSignal,
        *,
        processing_time: datetime | None = None,
    ) -> TranslationResult:
        """Translate strike signal into impact."""
        prob = signal.original_event.probability
        title_lower = signal.original_event.title.lower()

        is_port_strike = any(
            kw in title_lower
            for kw in ["port", "dock", "longshore", "terminal"]
        )
        if is_port_strike:
            productivity_loss, source = get_param(
                STRIKE_PARAMS, "port_strike_productivity_loss_pct"
            )
        else:
            productivity_loss, source = get_param(
                STRIKE_PARAMS, "truck_strike_capacity_loss_pct"
            )

        duration_days, duration_source = get_param(
            STRIKE_PARAMS, "strike_duration_avg_days"
        )

        metrics = [
            ImpactMetric(
                name="capacity_loss",
                value=round(productivity_loss * prob, 1),
                unit="percent",
                uncertainty=UncertaintyBounds(
                    lower=round(productivity_loss * prob * 0.5, 1),
                    upper=round(productivity_loss * prob * 1.0, 1),
                ),
                confidence=0.65,
                baseline=0,
                evidence_type="historical",
                evidence_source=source,
            ),
            ImpactMetric(
                name="expected_duration",
                value=round(duration_days * prob, 1),
                unit="days",
                uncertainty=UncertaintyBounds(
                    lower=round(duration_days * prob * 0.5, 1),
                    upper=round(duration_days * prob * 3.0, 1),
                ),
                confidence=0.5,
                baseline=0,
                evidence_type="historical",
                evidence_source=duration_source,
            ),
        ]

        severity = min(prob * 0.8, 1.0)
        assumptions = [
            f"Productivity/capacity loss: {productivity_loss}% ({source})",
            f"Average strike duration: {duration_days} days ({duration_source})",
            "Impact assumes no contingency plans in place",
        ]

        ts = processing_time if processing_time is not None else datetime.utcnow()
        return TranslationResult(
            applicable=True,
            metrics=metrics,
            affected_routes=[],
            affected_systems=[],
            severity_contribution=severity,
            assumptions=assumptions,
            explanation=self._build_explanation(signal, metrics, severity, ts),
        )

    def _build_explanation(
        self,
        signal: ValidatedSignal,
        metrics: list[ImpactMetric],
        severity: float,
        processing_time: datetime,
    ) -> ExplanationStep:
        return ExplanationStep.create(
            step_id=1,
            rule_name=self.name,
            rule_version=self.version,
            reasoning=(
                f"Strike signal at {signal.original_event.probability:.0%}. "
                f"Capacity loss: {metrics[0].value:.1f}%, "
                f"duration: {metrics[1].value:.1f} days."
            ),
            confidence_contribution=0.65,
            processing_time=processing_time,
            input_summary={"probability": signal.original_event.probability},
            output_summary={
                "capacity_loss": metrics[0].value,
                "severity": severity,
            },
        )
