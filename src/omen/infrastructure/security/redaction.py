"""
Field redaction for external data sharing and secret redaction for logs.
"""

import logging
import re
from typing import Any

from omen.domain.models.omen_signal import OmenSignal

# Patterns to redact from log/string output (secrets)
REDACT_PATTERNS = [
    (re.compile(r'(api[_-]?key["\s:=]+)["\']?[\w.-]+["\']?', re.I), r"\1[REDACTED]"),
    (re.compile(r'(password["\s:=]+)["\']?[\w.-]+["\']?', re.I), r"\1[REDACTED]"),
    (re.compile(r'(secret["\s:=]+)["\']?[\w.-]+["\']?', re.I), r"\1[REDACTED]"),
    (re.compile(r'(bearer\s+)[\w.-]+', re.I), r"\1[REDACTED]"),
    (re.compile(r'(authorization["\s:=]+)["\']?[\w.-]+["\']?', re.I), r"\1[REDACTED]"),
    (re.compile(r"omen_[\w.-]{32,}", re.I), "[REDACTED_KEY]"),
]


def redact_secrets(text: str) -> str:
    """Redact sensitive data from text (for logs, error messages)."""
    for pattern, replacement in REDACT_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


def redact_dict(data: dict[str, Any]) -> dict[str, Any]:
    """Redact sensitive data from dictionary (keys and string values)."""
    sensitive_keys = {"api_key", "password", "secret", "token", "authorization"}
    result: dict[str, Any] = {}
    for key, value in data.items():
        if key.lower() in sensitive_keys:
            result[key] = "[REDACTED]"
        elif isinstance(value, dict):
            result[key] = redact_dict(value)
        elif isinstance(value, str):
            result[key] = redact_secrets(value)
        else:
            result[key] = value
    return result


class RedactingFormatter(logging.Formatter):
    """Log formatter that redacts secrets from the formatted message."""

    def format(self, record: logging.LogRecord) -> str:
        original = super().format(record)
        return redact_secrets(original)


class RedactingWrapperFormatter(logging.Formatter):
    """Wraps another formatter and redacts secrets from its output."""

    def __init__(self, inner: logging.Formatter) -> None:
        super().__init__()
        self._inner = inner

    def format(self, record: logging.LogRecord) -> str:
        original = self._inner.format(record)
        return redact_secrets(original)

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
