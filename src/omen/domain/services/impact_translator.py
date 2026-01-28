"""Layer 3 orchestration: Impact translation service."""

import logging
from datetime import datetime
from typing import List

from omen.domain.models.validated_signal import ValidatedSignal
from omen.domain.models.impact_assessment import (
    ImpactAssessment,
    ImpactMetric,
    AffectedRoute,
    AffectedSystem,
    UncertaintyBounds,
)
from omen.domain.models.common import ImpactDomain, RulesetVersion
from omen.domain.models.context import ProcessingContext
from omen.domain.models.explanation import ExplanationChain, ExplanationStep
from omen.domain.rules.translation.base import ImpactTranslationRule, TranslationResult
from omen.domain.methodology.red_sea_impact import TIMING_METHODOLOGY


logger = logging.getLogger(__name__)


def _extract_regions_from_title(title: str) -> list[str]:
    """Extract region/location hints from title for fallback assessment."""
    regions: list[str] = []
    title_lower = (title or "").lower()
    region_keywords = {
        "red sea": "Red Sea",
        "suez": "Suez",
        "panama": "Panama",
        "asia": "Asia",
        "europe": "Europe",
        "china": "China",
        "middle east": "Middle East",
        "africa": "Africa",
        "america": "America",
        "pacific": "Pacific",
        "atlantic": "Atlantic",
        "mediterranean": "Mediterranean",
        "gulf": "Gulf",
        "strait": "Strait",
    }
    for keyword, region in region_keywords.items():
        if keyword in title_lower and region not in regions:
            regions.append(region)
    return regions[:2]


class ImpactTranslator:
    """Orchestrates translation rules to produce ImpactAssessment."""

    def __init__(
        self,
        rules: List[ImpactTranslationRule],
        fallback_enabled: bool = True,
    ):
        """
        Initialize impact translator.

        Args:
            rules: List of translation rules to try
            fallback_enabled: If True, when no rule matches for LOGISTICS,
                return a generic "Potential Warning" assessment.
        """
        self.rules = rules
        self._fallback_enabled = fallback_enabled

    def translate(
        self,
        signal: ValidatedSignal,
        domain: ImpactDomain,
        context: ProcessingContext,
    ) -> ImpactAssessment | None:
        """
        Translate validated signal into impact assessment.

        Catches rule errors and continues with other rules.
        Returns None if no rules produced results.
        When fallback_enabled and domain is LOGISTICS, returns a generic
        "Potential Warning" assessment if no rule matches.
        """
        applicable_rules = [
            r for r in self.rules
            if r.domain == domain and r.is_applicable(signal)
        ]
        if not applicable_rules:
            if self._fallback_enabled and domain == ImpactDomain.LOGISTICS:
                return self._create_fallback_assessment(signal, domain, context)
            return None

        applicable_results_with_names: List[tuple[str, TranslationResult]] = []
        rule_errors: List[tuple[str, Exception]] = []

        for rule in applicable_rules:
            try:
                result = rule.translate(
                    signal, processing_time=context.processing_time
                )
                if result.applicable:
                    applicable_results_with_names.append((rule.name, result))
            except Exception as e:
                logger.error(
                    "Translation rule %s raised exception: %s",
                    rule.name,
                    e,
                    exc_info=True,
                    extra={
                        "event_id": str(signal.event_id),
                        "rule": rule.name,
                        "domain": domain.value,
                    },
                )
                rule_errors.append((rule.name, e))

        if not applicable_results_with_names:
            if rule_errors:
                logger.warning(
                    "No applicable results for %s; %d rules errored",
                    signal.event_id,
                    len(rule_errors),
                )
            return None

        all_metrics: List[ImpactMetric] = []
        all_routes: List[AffectedRoute] = []
        all_systems: List[AffectedSystem] = []
        all_assumptions: List[str] = []
        explanation_steps: List[ExplanationStep] = []
        max_severity = 0.0
        applied_rule_names: List[str] = []

        for rule_name, result in applicable_results_with_names:
            all_metrics.extend(result.metrics)
            all_routes.extend(result.affected_routes)
            all_systems.extend(result.affected_systems)
            all_assumptions.extend(result.assumptions)
            if result.explanation:
                explanation_steps.append(result.explanation)
            max_severity = max(max_severity, result.severity_contribution)
            applied_rule_names.append(rule_name)

        if max_severity >= 0.8:
            severity_label = "CRITICAL"
        elif max_severity >= 0.6:
            severity_label = "HIGH"
        elif max_severity >= 0.4:
            severity_label = "MEDIUM"
        else:
            severity_label = "LOW"

        explanation_chain = ExplanationChain.create(context)
        steps_with_context_time: List[ExplanationStep] = []
        for i, step in enumerate(explanation_steps, start=1):
            step = step.model_copy(
                update={"step_id": i, "timestamp": context.processing_time}
            )
            steps_with_context_time.append(step)
            explanation_chain = explanation_chain.add_step(step)
        explanation_chain = explanation_chain.finalize(context)

        impact_summary = self._build_impact_summary(
            signal, all_metrics, all_routes, all_systems, max_severity
        )

        # Use documented timing methodology (fixes ISSUE-010)
        prob = signal.original_event.probability
        tp = TIMING_METHODOLOGY.parameters
        base_onset = int(tp["base_onset_hours"][0])
        urgency_factor = float(tp["urgency_factor"][0])
        base_duration = int(tp["base_duration_hours"][0])
        onset_hours = int(base_onset * (1.0 - prob * urgency_factor))
        duration_hours = base_duration

        return ImpactAssessment(
            event_id=signal.event_id,
            source_signal=signal,
            domain=domain,
            metrics=all_metrics,
            affected_routes=all_routes,
            affected_systems=all_systems,
            overall_severity=max_severity,
            severity_label=severity_label,
            expected_onset_hours=max(1, onset_hours),
            expected_duration_hours=duration_hours,
            explanation_steps=steps_with_context_time,
            explanation_chain=explanation_chain,
            impact_summary=impact_summary,
            assumptions=all_assumptions,
            ruleset_version=context.ruleset_version,
            translation_rules_applied=applied_rule_names,
            assessed_at=context.processing_time,
        )

    def _create_fallback_assessment(
        self,
        signal: ValidatedSignal,
        domain: ImpactDomain,
        context: ProcessingContext,
    ) -> ImpactAssessment:
        """
        Create a generic "Potential Warning" assessment when no rule matches.

        Used for LOGISTICS when fallback_enabled and event passed validation
        but no Red Sea / Panama / Strike etc. rule applied.
        """
        prob = signal.original_event.probability
        val = round(prob * 100, 1)
        low = round(prob * 80, 1)
        up = min(100.0, round(prob * 120, 1))

        generic_metric = ImpactMetric(
            name="potential_disruption_level",
            value=val,
            unit="percent",
            uncertainty=UncertaintyBounds(lower=low, upper=up, confidence_interval=0.8),
            confidence=0.5,
            baseline=0,
            evidence_type="assumption",
            evidence_source="Probability-based estimate (no specific model)",
            methodology_name="generic_probability_scaling",
            methodology_version="1.0.0",
        )

        if prob >= 0.7:
            severity = 0.8
            severity_label = "HIGH"
        elif prob >= 0.5:
            severity = 0.6
            severity_label = "MEDIUM"
        else:
            severity = 0.4
            severity_label = "LOW"

        regions = _extract_regions_from_title(signal.original_event.title)
        routes: List[AffectedRoute] = []
        if regions:
            origin = regions[0]
            dest = regions[1] if len(regions) > 1 else "Multiple"
            routes = [
                AffectedRoute(
                    route_id="generic-impact",
                    route_name="Potential Impact Zone",
                    origin_region=origin,
                    destination_region=dest,
                    impact_severity=severity,
                    alternative_routes=[],
                    estimated_delay_days=None,
                    delay_uncertainty=None,
                )
            ]

        reasoning = (
            f"No specific translation rule matched. Generated generic assessment "
            f"based on probability ({prob:.0%}) and logistics relevance. "
            f"Manual review recommended."
        )
        step = ExplanationStep.create(
            step_id=1,
            rule_name="fallback_translation",
            rule_version="1.0.0",
            reasoning=reasoning,
            confidence_contribution=0.5,
            processing_time=context.processing_time,
            input_summary={
                "event_probability": prob,
                "category": signal.category.value,
            },
            output_summary={
                "potential_disruption_level": val,
                "severity": severity,
                "severity_label": severity_label,
            },
        )
        chain = ExplanationChain.create(context).add_step(step).finalize(context)

        tp = TIMING_METHODOLOGY.parameters
        base_onset = int(tp["base_onset_hours"][0])
        urgency_factor = float(tp["urgency_factor"][0])
        base_duration = int(tp["base_duration_hours"][0])
        onset_hours = max(1, int(base_onset * (1.0 - prob * urgency_factor)))

        summary = (
            f"Signal indicates {prob:.0%} probability. Generic logistics impact "
            f"(potential disruption level {val}%). No specific model applied; review recommended."
        )

        return ImpactAssessment(
            event_id=signal.event_id,
            source_signal=signal,
            domain=domain,
            metrics=[generic_metric],
            affected_routes=routes,
            affected_systems=[],
            overall_severity=severity,
            severity_label=severity_label,
            expected_onset_hours=onset_hours,
            expected_duration_hours=base_duration,
            explanation_steps=[step],
            explanation_chain=chain,
            impact_summary=summary,
            assumptions=[
                "No specific translation rule matched; generic probability-based assessment.",
                "Manual review recommended for operational decisions.",
            ],
            ruleset_version=context.ruleset_version,
            translation_rules_applied=[],
            assessed_at=context.processing_time,
            is_fallback=True,
            requires_review=True,
            fallback_reason="No applicable translation rule matched for this event.",
        )

    def _build_impact_summary(
        self,
        signal: ValidatedSignal,
        metrics: List[ImpactMetric],
        routes: List[AffectedRoute],
        systems: List[AffectedSystem],
        severity: float,
    ) -> str:
        """Build human-readable impact summary."""
        lines = [
            f"Signal indicates {signal.original_event.probability:.0%} probability of {signal.category.value.lower()} event."
        ]
        if metrics:
            lines.append("Expected impacts:")
            for metric in metrics[:3]:
                lines.append(f"  • {metric.name}: {metric.value} {metric.unit}")
        if routes:
            lines.append(f"Affected routes: {len(routes)}")
            for route in routes[:2]:
                lines.append(f"  • {route.route_name}")
        if systems:
            lines.append(f"Affected systems: {len(systems)}")
            for system in systems[:2]:
                lines.append(f"  • {system.system_name}")
        return " ".join(lines)
