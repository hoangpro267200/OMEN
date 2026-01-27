"""
Input validation and sanitization for OMEN.
"""

import re
from typing import Any

from pydantic import BaseModel, field_validator

# Dangerous patterns to reject
DANGEROUS_PATTERNS = [
    r"<script.*?>.*?</script>",
    r"javascript:",
    r"on\w+\s*=",
    r"\{\{.*?\}\}",
    r"\$\{.*?\}",
]

COMPILED_PATTERNS = [
    re.compile(p, re.IGNORECASE | re.DOTALL) for p in DANGEROUS_PATTERNS
]


def sanitize_string(value: str, max_length: int = 10000) -> str:
    """
    Sanitize a string input.

    - Truncates to max length
    - Removes null bytes
    - Checks for dangerous patterns
    """
    if not value:
        return value

    value = value[:max_length]
    value = value.replace("\x00", "")

    for pattern in COMPILED_PATTERNS:
        if pattern.search(value):
            raise ValueError("Input contains potentially dangerous content")

    return value


def sanitize_dict(data: dict[str, Any], max_depth: int = 10) -> dict[str, Any]:
    """Recursively sanitize a dictionary."""
    if max_depth <= 0:
        raise ValueError("Input nested too deeply")

    result: dict[str, Any] = {}
    for key, value in data.items():
        if isinstance(key, str):
            key = sanitize_string(key, max_length=100)

        if isinstance(value, str):
            value = sanitize_string(value)
        elif isinstance(value, dict):
            value = sanitize_dict(value, max_depth - 1)
        elif isinstance(value, list):
            value = [
                sanitize_dict(v, max_depth - 1)
                if isinstance(v, dict)
                else sanitize_string(v)
                if isinstance(v, str)
                else v
                for v in value
            ]

        result[key] = value

    return result


class SecureEventInput(BaseModel):
    """
    Secure input model for external event submission.

    Validates and sanitizes all fields.
    """

    event_id: str
    title: str
    description: str | None = None
    probability: float
    source: str

    @field_validator("event_id")
    @classmethod
    def validate_event_id(cls, v: str) -> str:
        v = sanitize_string(v, max_length=100)
        if not re.match(r"^[a-zA-Z0-9_-]+$", v):
            raise ValueError(
                "event_id must be alphanumeric with hyphens/underscores only"
            )
        return v

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        return sanitize_string(v, max_length=500)

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: str | None) -> str | None:
        if v is None:
            return None
        return sanitize_string(v, max_length=5000)

    @field_validator("probability")
    @classmethod
    def validate_probability(cls, v: float) -> float:
        if not 0 <= v <= 1:
            raise ValueError("probability must be between 0 and 1")
        return v

    @field_validator("source")
    @classmethod
    def validate_source(cls, v: str) -> str:
        v = sanitize_string(v, max_length=50)
        allowed_sources = {"polymarket", "kalshi", "metaculus", "manual", "test"}
        if v.lower() not in allowed_sources:
            raise ValueError(f"source must be one of: {allowed_sources}")
        return v.lower()
