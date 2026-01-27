"""
Generate human-readable explanation reports and machine-readable audit trails.
"""

from omen.domain.models.omen_signal import OmenSignal


def generate_text_report(signal: OmenSignal) -> str:
    """
    Generate a human-readable explanation report.

    Suitable for:
    - Email notifications
    - Slack messages
    - Log files
    """
    lines = [
        "=" * 60,
        f"OMEN SIGNAL REPORT: {signal.signal_id}",
        "=" * 60,
        "",
        "SUMMARY",
        "-" * 40,
        f"Title: {signal.title}",
        f"Confidence: {signal.confidence_level.value} ({signal.confidence_score:.0%})",
        f"Severity: {signal.severity_label} ({signal.severity:.0%})",
        f"Actionable: {'Yes' if signal.is_actionable else 'No'}",
        f"Urgency: {signal.urgency}",
        "",
    ]

    if signal.key_metrics:
        lines.append("KEY METRICS")
        lines.append("-" * 40)
        for metric in signal.key_metrics:
            uncertainty_str = ""
            if metric.uncertainty:
                uncertainty_str = (
                    f" (range: {metric.uncertainty.lower}-{metric.uncertainty.upper})"
                )
            lines.append(
                f"  • {metric.name}: {metric.value} {metric.unit}{uncertainty_str}"
            )
            if metric.evidence_source:
                lines.append(f"    Source: {metric.evidence_source}")
        lines.append("")

    if signal.affected_routes:
        lines.append("AFFECTED ROUTES")
        lines.append("-" * 40)
        for route in signal.affected_routes:
            lines.append(f"  • {route.route_name}")
            lines.append(f"    {route.origin_region} → {route.destination_region}")
            lines.append(f"    Severity: {route.impact_severity:.0%}")
        lines.append("")

    lines.append("REASONING CHAIN")
    lines.append("-" * 40)
    for step in signal.explanation_chain.steps:
        lines.append(step.to_human_readable())
        lines.append("")

    lines.append("REPRODUCIBILITY")
    lines.append("-" * 40)
    lines.append(f"Input Hash: {signal.input_event_hash}")
    lines.append(f"Trace ID: {signal.deterministic_trace_id}")
    lines.append(f"Ruleset: {signal.ruleset_version}")
    lines.append(f"Generated: {signal.generated_at.isoformat()}")

    return "\n".join(lines)


def generate_json_audit_report(signal: OmenSignal) -> dict:
    """
    Generate machine-readable audit report.

    Suitable for:
    - Compliance systems
    - Data warehouses
    - Audit trails
    """
    return {
        "signal_id": signal.signal_id,
        "event_id": str(signal.event_id),
        "reproducibility": {
            "input_event_hash": signal.input_event_hash,
            "deterministic_trace_id": signal.deterministic_trace_id,
            "ruleset_version": str(signal.ruleset_version),
        },
        "classification": {
            "category": signal.category.value,
            "subcategory": signal.subcategory,
            "domain": signal.domain.value,
        },
        "assessment": {
            "confidence_level": signal.confidence_level.value,
            "confidence_score": signal.confidence_score,
            "confidence_factors": signal.confidence_factors,
            "severity": signal.severity,
            "severity_label": signal.severity_label,
            "is_actionable": signal.is_actionable,
            "urgency": signal.urgency,
        },
        "metrics": [
            {
                "name": m.name,
                "value": m.value,
                "unit": m.unit,
                "uncertainty": (
                    {
                        "lower": m.uncertainty.lower,
                        "upper": m.uncertainty.upper,
                    }
                    if m.uncertainty
                    else None
                ),
                "confidence": m.confidence,
                "evidence_type": m.evidence_type,
                "evidence_source": m.evidence_source,
            }
            for m in signal.key_metrics
        ],
        "affected_infrastructure": {
            "routes": [r.model_dump() for r in signal.affected_routes],
            "systems": [s.model_dump() for s in signal.affected_systems],
            "regions": signal.affected_regions,
        },
        "explanation_chain": {
            "trace_id": signal.explanation_chain.trace_id,
            "total_steps": signal.explanation_chain.total_steps,
            "steps": [s.to_audit_format() for s in signal.explanation_chain.steps],
            "started_at": signal.explanation_chain.started_at.isoformat(),
            "completed_at": (
                signal.explanation_chain.completed_at.isoformat()
                if signal.explanation_chain.completed_at
                else None
            ),
        },
        "source": {
            "market": signal.source_market,
            "url": signal.market_url,
        },
        "timestamps": {
            "generated_at": signal.generated_at.isoformat(),
        },
    }
