"""
Generate human-readable explanation reports and machine-readable audit trails.

Uses the pure OmenSignal contract only (probability, confidence, evidence, trace_id).
"""

from omen.domain.models.omen_signal import OmenSignal


def generate_text_report(signal: OmenSignal) -> str:
    """
    Generate a human-readable explanation report for a pure OmenSignal.
    """
    lines = [
        "=" * 60,
        f"OMEN SIGNAL REPORT: {signal.signal_id}",
        "=" * 60,
        "",
        "SUMMARY",
        "-" * 40,
        f"Title: {signal.title}",
        f"Probability: {signal.probability:.0%} ({signal.probability_source})",
        f"Confidence: {signal.confidence_level.value} ({signal.confidence_score:.0%})",
        f"Category: {signal.category.value}",
        "",
    ]

    if signal.validation_scores:
        lines.append("VALIDATION SCORES")
        lines.append("-" * 40)
        for vs in signal.validation_scores:
            lines.append(f"  • {vs.rule_name} ({vs.rule_version}): {vs.score:.0%} — {vs.reasoning}")
        lines.append("")

    if signal.evidence:
        lines.append("EVIDENCE")
        lines.append("-" * 40)
        for ev in signal.evidence:
            lines.append(f"  • {ev.source} ({ev.source_type})")
            if ev.url:
                lines.append(f"    {ev.url}")
        lines.append("")

    lines.append("REPRODUCIBILITY")
    lines.append("-" * 40)
    lines.append(f"Input Hash: {signal.input_event_hash or '—'}")
    lines.append(f"Trace ID: {signal.trace_id}")
    lines.append(f"Ruleset: {signal.ruleset_version}")
    lines.append(f"Generated: {signal.generated_at.isoformat()}")

    return "\n".join(lines)


def generate_json_audit_report(signal: OmenSignal) -> dict:
    """
    Generate machine-readable audit report for a pure OmenSignal.
    """
    return {
        "signal_id": signal.signal_id,
        "source_event_id": signal.source_event_id,
        "reproducibility": {
            "input_event_hash": signal.input_event_hash,
            "trace_id": signal.trace_id,
            "ruleset_version": str(signal.ruleset_version),
        },
        "classification": {
            "category": signal.category.value,
            "tags": signal.tags,
            "keywords_matched": signal.keywords_matched,
        },
        "assessment": {
            "confidence_level": signal.confidence_level.value,
            "confidence_score": signal.confidence_score,
            "confidence_factors": signal.confidence_factors,
        },
        "probability": {
            "value": signal.probability,
            "source": signal.probability_source,
            "is_estimate": signal.probability_is_estimate,
        },
        "validation_scores": [vs.model_dump() for vs in signal.validation_scores],
        "evidence": [e.model_dump(mode="json") for e in signal.evidence],
        "geographic": signal.geographic.model_dump(),
        "temporal": signal.temporal.model_dump(mode="json"),
        "source_url": signal.source_url,
        "generated_at": signal.generated_at.isoformat(),
    }
