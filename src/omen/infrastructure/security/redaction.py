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
    Redact an OmenSignal (pure contract) for external consumption.
    """
    data = signal.model_dump(mode="json")

    for field_name in ALWAYS_REDACT:
        data.pop(field_name, None)

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
    Redact signal (pure contract) for API response.

    Args:
        signal: The signal
        detail_level: One of "minimal", "standard", "full"
    """
    if detail_level == "minimal":
        return {
            "signal_id": signal.signal_id,
            "source_event_id": signal.source_event_id,
            "title": signal.title,
            "probability": signal.probability,
            "confidence_level": signal.confidence_level.value,
            "trace_id": signal.trace_id,
            "generated_at": signal.generated_at.isoformat(),
        }
    if detail_level == "full":
        return redact_signal_for_external(
            signal,
            include_confidence_breakdown=True,
        )
    return redact_signal_for_external(signal)
