"""
Field redaction for external data sharing.
"""

from typing import Any

from omen.domain.models.omen_signal import OmenSignal

# Fields to always redact when publishing externally
ALWAYS_REDACT = {
    "_source_assessment",
    "raw_payload",
}


def redact_signal_for_external(
    signal: OmenSignal,
    include_explanation: bool = False,
    include_confidence_breakdown: bool = False,
) -> dict[str, Any]:
    """
    Redact an OmenSignal for external consumption.

    Args:
        signal: The signal to redact
        include_explanation: Whether to include full explanation chain
        include_confidence_breakdown: Whether to include confidence factors

    Returns:
        Redacted dictionary representation
    """
    data = signal.model_dump(mode="json")

    for field_name in ALWAYS_REDACT:
        data.pop(field_name, None)

    if not include_explanation:
        if "explanation_chain" in data:
            chain = data["explanation_chain"]
            data["explanation_summary"] = {
                "trace_id": chain.get("trace_id"),
                "total_steps": chain.get("total_steps"),
                "started_at": chain.get("started_at"),
                "completed_at": chain.get("completed_at"),
            }
            del data["explanation_chain"]

    if not include_confidence_breakdown:
        if "confidence_factors" in data:
            factors = data["confidence_factors"]
            if factors and isinstance(factors, dict):
                vals = [v for v in factors.values() if isinstance(v, (int, float))]
                data["confidence_factors"] = (
                    {"aggregate": sum(vals) / len(vals)} if vals else {}
                )

    return data


def redact_for_webhook(signal: OmenSignal) -> dict[str, Any]:
    """Redact signal for webhook delivery."""
    return redact_signal_for_external(
        signal,
        include_explanation=False,
        include_confidence_breakdown=False,
    )


def redact_for_api(
    signal: OmenSignal,
    detail_level: str = "standard",
) -> dict[str, Any]:
    """
    Redact signal for API response.

    Args:
        signal: The signal
        detail_level: One of "minimal", "standard", "full"
    """
    if detail_level == "minimal":
        return {
            "signal_id": signal.signal_id,
            "title": signal.title,
            "confidence_level": signal.confidence_level.value,
            "severity": signal.severity,
            "is_actionable": signal.is_actionable,
            "urgency": signal.urgency,
            "generated_at": signal.generated_at.isoformat(),
        }
    if detail_level == "full":
        return redact_signal_for_external(
            signal,
            include_explanation=True,
            include_confidence_breakdown=True,
        )
    return redact_signal_for_external(signal)
