"""Layer 3 orchestration: Impact translation service."""

import logging
from typing import List

from omen.domain.models.validated_signal import ValidatedSignal
from omen.domain.models.impact_assessment import (
    ImpactAssessment,
    ImpactMetric,
    AffectedRoute,
    AffectedSystem,
)
from omen.domain.models.common import ImpactDomain, RulesetVersion
from omen.domain.models.context import ProcessingContext
from omen.domain.models.explanation import ExplanationChain, ExplanationStep
from omen.domain.rules.translation.base import ImpactTranslationRule, TranslationResult
from omen.domain.methodology.red_sea_impact import TIMING_METHODOLOGY


logger = logging.getLogger(__name__)


class ImpactTranslator:
    """Orchestrates translation rules to produce ImpactAssessment."""

    def __init__(self, rules: List[ImpactTranslationRule]):
        """
        Initialize impact translator.

        Args:
            rules: List of translation rules to try
        """
        self.rules = rules

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
        All timestamps derive from context for deterministic replay.
        """
        applicable_rules = [
            r for r in self.rules
            if r.domain == domain and r.is_applicable(signal)
        ]
        if not applicable_rules:
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
