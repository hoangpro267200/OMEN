"""Port Closure Translation Rule. Translates port closure/congestion signals into logistics impacts."""

from datetime import datetime

from omen.domain.models.common import ImpactDomain, SignalCategory
from omen.domain.models.validated_signal import ValidatedSignal
from omen.domain.models.explanation import ExplanationStep

from omen_impact.assessment import ImpactMetric, UncertaintyBounds, AffectedSystem
from omen_impact.rules.base import BaseTranslationRule, TranslationResult
from omen_impact.rules.logistics.parameters import PORT_CLOSURE_PARAMS, get_param


class PortClosureRule(BaseTranslationRule):
    """Translates port closure signals into logistics impacts."""

    @property
    def name(self) -> str:
        return "port_closure_logistics"

    @property
    def version(self) -> str:
        return "2.0.0"

    @property
    def domain(self) -> ImpactDomain:
        return ImpactDomain.LOGISTICS

    @property
    def applicable_categories(self) -> set[SignalCategory]:
        return {SignalCategory.INFRASTRUCTURE, SignalCategory.CLIMATE, SignalCategory.LABOR}

    @property
    def applicable_keywords(self) -> set[str]:
        return {"port closure", "port shutdown", "terminal closure", "port congestion", "berth", "dock", "terminal"}

    def _custom_applicability_check(self, signal: ValidatedSignal) -> bool:
        text = (f"{signal.original_event.title} {signal.original_event.description or ''}").lower()
        return any(ind in text for ind in ["port of", "port ", "terminal", "harbor", "harbour"])

    def translate(
        self,
        signal: ValidatedSignal,
        *,
        processing_time: datetime | None = None,
    ) -> TranslationResult:
        prob = signal.original_event.probability
        congestion_rate, congestion_source = get_param(PORT_CLOSURE_PARAMS, "congestion_buildup_rate")
        diversion_cost, diversion_source = get_param(PORT_CLOSURE_PARAMS, "diversion_cost_increase_pct")
        estimated_duration_days = 5
        delay_days = congestion_rate * estimated_duration_days * prob

        metrics = [
            ImpactMetric(name="port_delay", value=round(delay_days, 1), unit="days",
                uncertainty=UncertaintyBounds(lower=round(delay_days * 0.5, 1), upper=round(delay_days * 2.0, 1)),
                confidence=0.6, baseline=0, evidence_type="model", evidence_source=congestion_source),
            ImpactMetric(name="diversion_cost_increase", value=round(diversion_cost * prob, 1), unit="percent",
                uncertainty=UncertaintyBounds(lower=round(diversion_cost * prob * 0.7, 1), upper=round(diversion_cost * prob * 1.5, 1)),
                confidence=0.5, baseline=0, evidence_type="historical", evidence_source=diversion_source),
        ]
        severity = min(prob * 0.9, 1.0)
        port_name = "Unknown Port"
        if "port of " in signal.original_event.title.lower():
            start = signal.original_event.title.lower().index("port of ") + 8
            end = min(start + 20, len(signal.original_event.title))
            chunk = signal.original_event.title[start:end].split()
            port_name = chunk[0].title() if chunk else "Unknown"
        affected_systems = [
            AffectedSystem(system_id=f"PORT-{port_name.upper().replace(' ', '-')}", system_name=port_name,
                system_type="PORT", impact_severity=severity, expected_duration_hours=estimated_duration_days * 24)
        ]
        assumptions = [
            f"Congestion builds at {congestion_rate} days delay per closure day ({congestion_source})",
            f"Diversion to alternative ports costs +{diversion_cost}% ({diversion_source})",
            f"Estimated closure duration: {estimated_duration_days} days",
        ]
        ts = processing_time if processing_time is not None else datetime.utcnow()
        explanation = ExplanationStep.create(
            step_id=1, rule_name=self.name, rule_version=self.version,
            reasoning=f"Port closure signal at {prob:.0%} probability. Expected delay: {metrics[0].value:.1f} days, diversion cost: +{metrics[1].value:.1f}%.",
            confidence_contribution=0.6, processing_time=ts,
            input_summary={"probability": prob}, output_summary={"delay_days": metrics[0].value, "severity": severity},
        )
        return TranslationResult(
            applicable=True, metrics=metrics, affected_routes=[], affected_systems=affected_systems,
            severity_contribution=severity, assumptions=assumptions, explanation=explanation,
        )
