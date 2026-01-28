"""
Red Sea Disruption Translation Rule.

Translates Red Sea/Suez disruption signals into logistics impacts
with evidence-based parameters and uncertainty bounds.
All calculations reference documented methodologies (Phase 5).
"""

from datetime import datetime

from ....models.common import ImpactDomain, SignalCategory
from ....models.validated_signal import ValidatedSignal
from ....models.impact_assessment import (
    ImpactMetric,
    UncertaintyBounds,
    AffectedRoute,
    AffectedSystem,
)
from ....models.explanation import ExplanationStep
from ....methodology.red_sea_impact import (
    TRANSIT_TIME_METHODOLOGY,
    FUEL_COST_METHODOLOGY,
    FREIGHT_RATE_METHODOLOGY,
    INSURANCE_METHODOLOGY,
)
from ..base import BaseTranslationRule, TranslationResult
from .parameters import RED_SEA_PARAMS, get_param


class RedSeaDisruptionRule(BaseTranslationRule):
    """
    Translates Red Sea disruption signals into logistics impacts.

    Evidence-based logic chain:
    1. Red Sea disruption → vessels reroute via Cape of Good Hope
    2. Reroute adds ~3000nm / ~10 days transit (Clarksons Research 2024)
    3. Fuel consumption increases ~30% (Lloyd's List 2024)
    4. Freight rates increase 15-100% depending on severity (Freightos 2024)
    5. Insurance premiums increase ~50% (Lloyd's of London 2024)

    All parameters are documented in parameters.py with sources.
    """

    @property
    def name(self) -> str:
        return "red_sea_disruption_logistics"

    @property
    def version(self) -> str:
        return "2.0.0"  # Major version: added uncertainty and evidence

    @property
    def domain(self) -> ImpactDomain:
        return ImpactDomain.LOGISTICS

    @property
    def applicable_categories(self) -> set[SignalCategory]:
        return {SignalCategory.GEOPOLITICAL, SignalCategory.INFRASTRUCTURE}

    @property
    def applicable_keywords(self) -> set[str]:
        return {
            "red sea",
            "suez",
            "houthi",
            "yemen",
            "bab el-mandeb",
            "gulf of aden",
            "shipping attack",
        }

    @property
    def applicable_chokepoints(self) -> set[str]:
        return {"Suez Canal", "Red Sea", "Bab el-Mandeb Strait"}

    def translate(
        self,
        signal: ValidatedSignal,
        *,
        processing_time: datetime | None = None,
    ) -> TranslationResult:
        """Perform evidence-based translation with uncertainty."""
        prob = signal.original_event.probability

        # Get evidence-based parameters
        transit_days, transit_source = get_param(
            RED_SEA_PARAMS, "reroute_transit_increase_days"
        )
        fuel_pct, fuel_source = get_param(
            RED_SEA_PARAMS, "fuel_consumption_increase_pct"
        )
        insurance_pct, insurance_source = get_param(
            RED_SEA_PARAMS, "insurance_premium_increase_pct"
        )

        # Determine freight rate based on probability (severity proxy)
        if prob >= 0.7:
            freight_pct, freight_source = get_param(
                RED_SEA_PARAMS, "freight_rate_increase_pct_crisis"
            )
        else:
            freight_pct, freight_source = get_param(
                RED_SEA_PARAMS, "freight_rate_increase_pct_base"
            )

        # Build metrics with uncertainty
        transit_val = round(transit_days * prob, 1)
        transit_unc = UncertaintyBounds(
            lower=round(7 * prob, 1),
            upper=round(14 * prob, 1),
        )
        fuel_val = round(fuel_pct * prob, 1)
        freight_val = round(freight_pct * prob, 1)
        insurance_val = round(insurance_pct * prob, 1)

        metrics = [
            ImpactMetric(
                name="transit_time_increase",
                value=transit_val,
                unit="days",
                uncertainty=transit_unc,
                confidence=0.8,
                baseline=0,
                evidence_type="historical",
                evidence_source=transit_source,
                sensitivity_to_probability=1.0,
            ),
            ImpactMetric(
                name="fuel_consumption_increase",
                value=fuel_val,
                unit="percent",
                uncertainty=UncertaintyBounds(
                    lower=round(fuel_pct * prob * 0.85, 1),
                    upper=round(fuel_pct * prob * 1.15, 1),
                ),
                confidence=0.75,
                baseline=0,
                evidence_type="historical",
                evidence_source=fuel_source,
                sensitivity_to_probability=1.0,
            ),
            ImpactMetric(
                name="freight_rate_pressure",
                value=freight_val,
                unit="percent",
                uncertainty=UncertaintyBounds(
                    lower=round(freight_pct * prob * 0.5, 1),
                    upper=round(freight_pct * prob * 2.0, 1),
                ),
                confidence=0.5,
                baseline=0,
                evidence_type="historical",
                evidence_source=freight_source,
                sensitivity_to_probability=1.3,
            ),
            ImpactMetric(
                name="insurance_premium_increase",
                value=insurance_val,
                unit="percent",
                uncertainty=UncertaintyBounds(
                    lower=round(insurance_pct * prob * 0.7, 1),
                    upper=round(insurance_pct * prob * 1.5, 1),
                ),
                confidence=0.7,
                baseline=0,
                evidence_type="historical",
                evidence_source=insurance_source,
                sensitivity_to_probability=1.0,
            ),
        ]

        base_severity = min(prob * 1.1, 1.0)

        # Affected routes
        affected_routes = [
            AffectedRoute(
                route_id="ASIA-EU-SUEZ",
                route_name="Asia to Europe (via Suez)",
                origin_region="East Asia",
                destination_region="Northern Europe",
                impact_severity=base_severity,
                alternative_routes=["Asia-EU-COGH (Cape of Good Hope)"],
                estimated_delay_days=metrics[0].value,
                delay_uncertainty=metrics[0].uncertainty,
            ),
            AffectedRoute(
                route_id="ASIA-MED-SUEZ",
                route_name="Asia to Mediterranean (via Suez)",
                origin_region="East Asia",
                destination_region="Mediterranean",
                impact_severity=base_severity * 0.9,
                alternative_routes=["Asia-MED-COGH"],
                estimated_delay_days=round(metrics[0].value * 0.9, 1),
                delay_uncertainty=None,
            ),
            AffectedRoute(
                route_id="MEA-EU-SUEZ",
                route_name="Middle East to Europe (via Suez)",
                origin_region="Middle East",
                destination_region="Europe",
                impact_severity=base_severity * 0.7,
                alternative_routes=["MEA-EU-COGH"],
                estimated_delay_days=round(metrics[0].value * 0.6, 1),
                delay_uncertainty=None,
            ),
        ]

        # Affected systems
        affected_systems = [
            AffectedSystem(
                system_id="SUEZ-CANAL",
                system_name="Suez Canal",
                system_type="CANAL",
                impact_severity=base_severity,
                expected_duration_hours=30 * 24,
            ),
            AffectedSystem(
                system_id="PORT-SAID",
                system_name="Port Said",
                system_type="PORT",
                impact_severity=base_severity * 0.8,
            ),
            AffectedSystem(
                system_id="JEDDAH",
                system_name="Jeddah Islamic Port",
                system_type="PORT",
                impact_severity=base_severity * 0.6,
            ),
        ]

        assumptions = [
            f"Vessels reroute via Cape of Good Hope, adding ~{transit_days} days ({transit_source})",
            f"Fuel consumption increases ~{fuel_pct}% on longer route ({fuel_source})",
            f"Freight rates increase {freight_pct}% based on current probability ({freight_source})",
            f"War risk insurance premiums increase ~{insurance_pct}% ({insurance_source})",
            "Impact scales with event probability",
            "Assumes no capacity constraints on Cape route",
        ]

        ts = processing_time if processing_time is not None else datetime.utcnow()

        # Attach methodology provenance to each metric
        methodology_by_index = [
            (TRANSIT_TIME_METHODOLOGY, "transit_time_increase"),
            (FUEL_COST_METHODOLOGY, "fuel_consumption_increase"),
            (FREIGHT_RATE_METHODOLOGY, "freight_rate_pressure"),
            (INSURANCE_METHODOLOGY, "insurance_premium_increase"),
        ]
        for i, (method, _) in enumerate(methodology_by_index):
            if i < len(metrics):
                m = metrics[i]
                metrics[i] = m.model_copy(
                    update={
                        "methodology_name": method.name,
                        "methodology_version": method.version,
                        "evidence_source": (
                            method.primary_source.to_string()
                            if method.primary_source
                            else m.evidence_source
                        ),
                        "calculation_inputs": {
                            "probability": prob,
                            "value_before_rounding": m.value,
                        },
                        "calculated_at": ts.isoformat(),
                    }
                )

        explanation = self._build_explanation(signal, metrics, base_severity, ts)

        return TranslationResult(
            applicable=True,
            metrics=metrics,
            affected_routes=affected_routes,
            affected_systems=affected_systems,
            severity_contribution=base_severity,
            assumptions=assumptions,
            explanation=explanation,
        )

    def _build_explanation(
        self,
        signal: ValidatedSignal,
        metrics: list[ImpactMetric],
        severity: float,
        processing_time: datetime,
    ) -> ExplanationStep:
        """Build detailed explanation with evidence citations."""
        prob = signal.original_event.probability
        m0, m1, m2 = metrics[0], metrics[1], metrics[2]
        reasoning = (
            f"Red Sea disruption signal at {prob:.0%} probability triggers rerouting analysis. "
            f"Based on Clarksons Research (2024), Cape of Good Hope reroute adds {m0.value:.1f} days "
            f"(range: {m0.uncertainty.lower:.1f}-{m0.uncertainty.upper:.1f}). "
            f"Lloyd's List data indicates {m1.value:.1f}% fuel consumption increase. "
            f"Freightos index suggests {m2.value:.1f}% freight rate pressure "
            f"(high uncertainty: {m2.uncertainty.lower:.1f}-{m2.uncertainty.upper:.1f}% due to market volatility). "
            f"Overall severity: {severity:.0%}."
        )
        return ExplanationStep.create(
            step_id=1,
            rule_name=self.name,
            rule_version=self.version,
            reasoning=reasoning,
            confidence_contribution=0.8,
            processing_time=processing_time,
            input_summary={
                "event_probability": prob,
                "category": signal.category.value,
                "chokepoints": signal.affected_chokepoints,
            },
            output_summary={
                "transit_increase_days": m0.value,
                "transit_uncertainty": f"{m0.uncertainty.lower}-{m0.uncertainty.upper}",
                "fuel_increase_pct": m1.value,
                "freight_pressure_pct": m2.value,
                "freight_uncertainty": f"{m2.uncertainty.lower}-{m2.uncertainty.upper}",
                "severity": severity,
                "evidence_sources": [m.evidence_source for m in metrics if m.evidence_source],
            },
        )
